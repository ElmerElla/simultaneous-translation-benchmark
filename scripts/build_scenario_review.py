"""Export one review row per published scenario, joined to its evidence and timing."""
import csv

from benchmark import ROOT, load, recompute


EVENT_IDS = {
    ('parley', 'R01'): ('W02',),
    ('parley', 'R02'): ('W03',),
    ('jotme', 'R01'): ('W02a', 'W02b'),
}
HEADERS = [
    'software', 'Scene ID', 'Test setup', 'Client or main subtitles F1–F5', 'Listen to page subtitles F1–F5', 'Enter the translated voice F1–F5',
    'Main subtitles complete fact count', 'Listen to page subtitles complete fact number', 'Complete number of translated facts',
    'First display seconds of main subtitles', 'Seconds to the first sound of video translation', 'Timing event ID', 'Timing and Attribution Instructions',
    'video file', 'Screenshot and video seconds', 'screenshot file', 'Round-by-round notes',
]


def display_facts(statuses):
    if not statuses:
        return '', ''
    observed = any(status not in ('Unconfirmed', 'Not observed in this run') for status in statuses)
    full = sum(status.startswith('Correct') for status in statuses)
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
            note = 'Video observations from the original acoustic starting point.'
            if (slug, ident) in EVENT_IDS or (slug == 'transync' and ident in ('W02', 'W03')):
                first_caption = first_voice = None
                note = 'Interruption and replay overlap, see timing.csv for specific events.'
            elif (slug, ident) == ('parley', 'R03'):
                note = 'No new output was observed after the tool was revoked until replayed.'
            elif (slug, ident) == ('parley', 'R04'):
                note = 'From the starting point of replaying the original sound, it cannot be automatically restored by quantization alone.'
            elif slug == 'iflytek' and ident.startswith('R'):
                note = 'The first subtitle comes from the client. The recorded voice translation cannot be uniquely assigned to the controlled listening page.'
            elif (slug, ident) == ('wordly', 'N01'):
                note = 'The listener will close the broadcast for this round.'
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
