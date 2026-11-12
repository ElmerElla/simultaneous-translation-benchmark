"""Portable, read-only checks and media analysis for the published benchmark.

All output text is UTF-8. No product login, network shaping or model download.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_media_path(directory, filename):
    directory = Path(directory).resolve()
    path = (directory / filename).resolve()
    if not path.is_relative_to(directory) or path == directory:
        raise ValueError('Media path must stay inside --media-dir')
    return path


def fact_counts(statuses):
    result = dict(confirmed=0, partial=0, error=0, omitted=0, unconfirmed=0)
    for status in statuses:
        if status.startswith('正确'):
            result['confirmed'] += 1
        elif status == '部分':
            result['partial'] += 1
        elif status == '错误':
            result['error'] += 1
        elif status == '遗漏':
            result['omitted'] += 1
        else:
            result['unconfirmed'] += 1
    return result


def latency(onset, first_output):
    if onset is None or first_output is None:
        return None
    if not math.isfinite(onset) or not math.isfinite(first_output):
        raise ValueError('Timestamps must be finite')
    return first_output - onset


def validate(root=ROOT, media_dir=None):
    root = Path(root)
    products = load(root / 'data/results.json')
    media = load(root / 'data/media-manifest.json')
    images = load(root / 'data/evidence-index.json')
    assert len(products) == 7
    assert len({p['slug'] for p in products}) == 7
    assert len(media) == 22 and len({m['id'] for m in media}) == len(media)
    assert len(images) == sum(len(p['cases']) for p in products) == 55
    by_id = {m['id']: m for m in media}
    for product in products:
        for case in product['cases']:
            assert case['video_id'] in by_id
            assert 0 <= case['pts_s'] < by_id[case['video_id']]['public_duration_s']
            assert (root / case['evidence_image']).is_file(), case['evidence_image']
            for key in ('subtitle', 'audio', 'receiver'):
                assert len(case.get(key, [])) in (0, 5), (product['slug'], case['id'], key)
    for m in media:
        assert m['review_status'] == 'reviewed', m['id']
        assert m['original_video_pts_at_public_zero_s'] == 0
        assert len(m['original_sha256']) == len(m['public_sha256']) == 64
        if media_dir is not None:
            path = safe_media_path(media_dir, m['file'])
            assert sha256(path) == m['public_sha256'], m['id']
    return dict(products=len(products), scenes=len(images), videos=len(media),
                media_hashes_checked=media_dir is not None)


def recompute(root=ROOT):
    rows = []
    for p in load(Path(root) / 'data/results.json'):
        for t in p['timing']:
            source = t.get('source_pts_s', t.get('source_pts'))
            subtitle = t.get('subtitle_pts_s', t.get('subtitle_pts'))
            audio = t.get('target_audio_pts_s', t.get('target_pts_s', t.get('audio_pts')))
            sub_delay = latency(source, subtitle)
            audio_delay = latency(source, audio)
            for derived, recorded in [(sub_delay, t.get('subtitle_delay_s', t.get('subtitle_latency'))),
                                      (audio_delay, t.get('audio_delay_s', t.get('audio_latency')))]:
                if derived is not None and recorded is not None:
                    assert abs(derived - recorded) < 1e-6, (p['slug'], t.get('id', t.get('scene')))
            rows.append(dict(product=p['slug'], scene=t.get('id', t.get('scene')),
                             video=t.get('video', 'V01'), subtitle_delay_s=sub_delay,
                             audio_delay_s=audio_delay))
    return rows


def media_stats(args):
    # This analyzes a user-supplied file. Public AAC copies do not reproduce raw metrics.
    import numpy as np
    if not (args.end > args.start >= 0):
        raise ValueError('Require 0 <= --start < --end')
    media = {m['id']: m for m in load(ROOT / 'data/media-manifest.json')}
    path = safe_media_path(args.media_dir, media[args.video]['file'])
    audio = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-nostdin', '-ss', str(args.start), '-i', str(path),
        '-t', str(args.end - args.start), '-map', '0:a:' + str(args.stream),
        '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'])
    values = np.frombuffer(audio, dtype='<f4')
    if values.size == 0:
        raise ValueError('No decoded audio samples')
    frame_count = values.size // 160
    frames = values[:frame_count * 160].reshape(-1, 160)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    active = np.flatnonzero(20 * np.log10(np.maximum(rms, 1e-12)) > args.threshold)
    return dict(video=args.video, stream=args.stream, sample_rate=16000,
                peak=float(np.abs(values).max()),
                clipped_fraction=float(np.mean(np.abs(values) >= .999)),
                threshold_dbfs=args.threshold,
                first_active_sample_window_s=(args.start + float(active[0]) * .01) if len(active) else None,
                note='公开AAC浏览副本的局部信号统计；不能替代原件音质、时延或MOS结论。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('validate', help='Check final records, evidence references and optional video hashes')
    check.add_argument('--media-dir', type=Path)
    calc = sub.add_parser('recompute', help='Recompute delays from the published original timestamps')
    calc.add_argument('--output', type=Path, help='Optional CSV output (UTF-8 BOM)')
    stats = sub.add_parser('stats', help='Inspect a public video audio interval without network access')
    stats.add_argument('--media-dir', type=Path, required=True)
    stats.add_argument('--video', required=True)
    stats.add_argument('--stream', type=int, default=0)
    stats.add_argument('--start', type=float, required=True)
    stats.add_argument('--end', type=float, required=True)
    stats.add_argument('--threshold', type=float, default=-42)
    args = parser.parse_args()
    if args.command == 'validate':
        result = validate(media_dir=args.media_dir)
    elif args.command == 'recompute':
        result = recompute()
        if args.output:
            with args.output.open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(result[0]))
                writer.writeheader()
                writer.writerows(result)
            result = dict(rows=len(result), output=str(args.output))
    else:
        result = media_stats(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
