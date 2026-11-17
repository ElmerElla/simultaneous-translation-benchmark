import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.videos = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('video', 'audio', 'img'):
            self.links.append(attrs['src'])
        if tag == 'video':
            self.videos.append(attrs['src'])
        if tag == 'a':
            self.links.append(attrs['href'])


class EnglishPublicationTests(unittest.TestCase):
    def test_documentation_and_data_are_english(self):
        files = [ROOT / 'README.md', ROOT / 'report.html']
        files += list((ROOT / 'docs').glob('*.md'))
        files += list((ROOT / 'data').rglob('*.json'))
        files += list((ROOT / 'data').rglob('*.csv'))
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertIsNone(re.search(r'[\u3400-\u9fff]', path.name))
                self.assertIsNone(re.search(r'[\u3400-\u9fff]', path.read_text(encoding='utf-8-sig')))

    def test_all_products_and_supplementary_videos_render_with_local_assets(self):
        html = (ROOT / 'report.html').read_text(encoding='utf-8')
        assets = Assets()
        assets.feed(html)
        self.assertIn('lang="en"', html)
        for product in json.loads((ROOT / 'data/results.json').read_text(encoding='utf-8')):
            self.assertIn(f'id="{product["slug"]}"', html)
        self.assertEqual(len(assets.videos), 21)
        for link in assets.links:
            if not link.startswith(('http:', 'https:', '#', 'mailto:')):
                self.assertTrue((ROOT / link.split('#')[0]).exists(), link)
        examples = json.loads((ROOT / 'data/parley-normal-20261116.json').read_text(encoding='utf-8'))
        self.assertFalse(examples['primary_normal_translation'])
        for recording in examples['recordings']:
            self.assertIn('media/' + recording['file'], assets.videos)


if __name__ == '__main__':
    unittest.main()
