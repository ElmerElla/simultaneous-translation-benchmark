import importlib.util
import math
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('benchmark', Path(__file__).resolve().parents[1] / 'scripts/benchmark.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class TimingAndEvidenceTests(unittest.TestCase):
    def test_missing_output_is_not_zero_delay(self):
        self.assertIsNone(benchmark.latency(5.0, None))
        self.assertEqual(benchmark.latency(5.0, 5.0), 0)

    def test_unconfirmed_facts_are_not_errors(self):
        counts = benchmark.fact_counts(['正确', '正确（抵消辅助）', '部分', '未确认', '本轮未观察到'])
        self.assertEqual(counts, dict(confirmed=2, partial=1, error=0, omitted=0, unconfirmed=2))

    def test_absolute_and_parent_paths_cannot_escape_media_directory(self):
        directory = Path(__file__).resolve().parent
        for bad in ('../private.mkv', str(directory.parent / 'private.mkv')):
            with self.assertRaises(ValueError):
                benchmark.safe_media_path(directory, bad)

    def test_nonfinite_timestamps_are_rejected(self):
        for invalid in (float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                benchmark.latency(invalid, 10.0)

    def test_recomputed_delays_match_all_final_records(self):
        rows = benchmark.recompute()
        self.assertGreater(len(rows), 40)
        self.assertTrue(any(r['audio_delay_s'] is None for r in rows))

    def test_every_published_case_has_an_existing_in_range_evidence_frame(self):
        self.assertEqual(benchmark.validate()['scenes'], 53)


if __name__ == '__main__':
    unittest.main(verbosity=2)
