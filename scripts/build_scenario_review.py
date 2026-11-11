"""Export one review row per published scenario, joined to its evidence and timing."""
import csv

from benchmark import ROOT, load, recompute


EVENT_IDS = {
    ('parley', 'R01'): ('W02',),
    ('parley', 'R02'): ('W03',),
    ('jotme', 'R01'): ('W02a', 'W02b'),
}
HEADERS = [
    '软件', '场景ID', '测试设置', '客户端或主字幕F1–F5', '收听页字幕F1–F5', '录入译声F1–F5',
    '主字幕完整事实数', '收听页字幕完整事实数', '译声完整事实数',
    '主字幕首显秒', '录像译声首响秒', '计时事件ID', '计时与归属说明',
    '录像文件', '截图录像秒', '截图文件', '逐轮备注',
]


def display_facts(statuses):
    if not statuses:
        return '', ''
    observed = any(status not in ('未确认', '本轮未观察到') for status in statuses)
    full = sum(status.startswith('正确') for status in statuses)
    return ' / '.join(statuses), full if observed else ''


def review_rows(root=ROOT):
    products = load(root / 'data/results.json')
    evidence = {(item['product'], item['case_id']): item for item in load(root / 'data/evidence-index.json')}
    media = {item['id']: item['file'] for item in load(root / 'data/media-manifest.json')}
    timing = {(row['product'], row['scene']): row for row in recompute(root)}
    for product in products:
        slug, name = product['slug'], product['name']
        for case in product['cases']:
            if case.get('adopted') is False:
                continue
            ident = case['id']
            frame = evidence[name, ident]
            assert (frame['image'], frame['video_id'], frame['original_pts_s']) == (
                case['evidence_image'], case['video_id'], case['pts_s']
            )
            texts, counts = zip(*(display_facts(case.get(key, [])) for key in ('subtitle', 'receiver', 'audio')))
            events = EVENT_IDS.get((slug, ident), (ident,))
            rows = [timing[slug, event] for event in events]
            first_caption, first_voice = rows[0]['subtitle_delay_s'], rows[0]['audio_delay_s']
            note = '从原声起点计的录像观测。'
            if (slug, ident) in EVENT_IDS or (slug == 'transync' and ident in ('W02', 'W03')):
                first_caption = first_voice = None
                note = '中断与重播交叠，具体事件见 timing.csv。'
            elif (slug, ident) == ('parley', 'R03'):
                note = '工具撤销后至重播前未观察到新输出。'
            elif (slug, ident) == ('parley', 'R04'):
                note = '从重播原声起点计，无法单独量化自动恢复。'
            elif slug == 'iflytek' and ident.startswith('R'):
                note = '首显来自客户端。录入译声无法唯一归属到受控收听页。'
            elif (slug, ident) == ('wordly', 'N01'):
                note = '本轮听众端关闭播音。'
            yield (
                name, ident, case['label'], *texts, *counts, first_caption, first_voice,
                ' / '.join(events), note, f'media/{media[frame["video_id"]]}',
                frame['original_pts_s'], frame['image'], case['note'],
            )


def main():
    output = ROOT / 'data/scenario-review.csv'
    rows = list(review_rows())
    with output.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    print(f'Exported {len(rows)} scenarios to data/scenario-review.csv')


if __name__ == '__main__':
    main()
