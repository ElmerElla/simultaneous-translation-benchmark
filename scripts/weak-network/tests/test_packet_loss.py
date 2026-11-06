import os as _publication_os
from pathlib import Path as _PublicationPath
import unittest
from verify_packet_loss import summarize,wilson

class PacketCountingTests(unittest.TestCase):
    def client(self):return dict(sent_qpc=[1]*10,received_qpc=[1]*8+[0,0],send_errors=0,receive_errors=0,duplicates=0)
    def peer(self):return dict(received_sequence=list(range(9)),sent_sequence=list(range(9)),send_errors=0,duplicates=0)
    def test_separate_direction_denominators(self):
        r=summarize(self.client(),self.peer());self.assertEqual(r['upstream']['loss_pct'],10);self.assertAlmostEqual(r['downstream']['loss_pct'],100/9);self.assertEqual(r['round_trip']['loss_pct'],20)
    def test_duplicate_sequence_not_double_counted(self):
        p=self.peer();p['received_sequence']+=[0,0];r=summarize(self.client(),p);self.assertEqual(r['upstream']['received'],9)
    def test_no_return_denominator_is_not_zero_percent(self):
        p=self.peer();p.update(received_sequence=[],sent_sequence=[]);c=self.client();c['received_qpc']=[0]*10;r=summarize(c,p);self.assertIsNone(r['downstream']['loss_pct']);self.assertEqual(r['upstream']['loss_pct'],100)
    def test_unexpected_sequences_are_reported(self):
        p=self.peer();p['received_sequence'].append(12);r=summarize(self.client(),p);self.assertEqual(r['unexpected_peer_sequence'],[12])
    def test_wilson_interval_contains_estimate(self):
        lo,hi=wilson(100,1000);self.assertLess(lo,10);self.assertGreater(hi,10)
    def test_wilson_boundaries_stay_in_percentage_range(self):
        for lost in (0,8000):
            lo,hi=wilson(lost,8000);self.assertGreaterEqual(lo,0);self.assertLessEqual(hi,100)

if __name__=='__main__':unittest.main(verbosity=2)
