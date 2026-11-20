import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_evaluation import initial_units
from a9_warmup import RenewalExponential


class TestFreshEvaluationUnits(unittest.TestCase):
    def inputs(self):
        truth = pd.DataFrame([dict(pn='PN', beta=2., eta=50., nu=.01)])
        channels = [dict(pn_index=0, pn='PN', aircraft='AC-01', channel=0,
                         curve=np.arange(821.), intervals=[(10, 800)], start=10, end=800),
                    dict(pn_index=0, pn='PN', aircraft='AC-01', channel=1,
                         curve=np.arange(821.), intervals=[(400, 800)], start=400, end=800)]
        return truth, channels

    def test_initial_age_zero_real_entry_and_late_entry_unchanged(self):
        truth, channels = self.inputs()
        entries = initial_units(truth, channels, 'calibrated', 'verification', 0, 730)
        self.assertEqual([e['start'] for e in entries], [10, 400])
        for entry in entries:
            self.assertEqual(entry['state'].age, 0.)
            self.assertEqual(entry['state'].renewal, 0)
            self.assertEqual(entry['state'].birth, entry['start'])
            self.assertEqual(entry['state'].time, entry['start'])
            self.assertEqual(entry['end'], 730)
            self.assertTrue(entry['unit'].startswith('EVAL-'))
            self.assertEqual(entry['aircraft'], 'AC-01')

    def test_evaluation_stream_is_common_across_policies_and_independent_of_auxiliary(self):
        truth, channels = self.inputs()
        first = initial_units(truth, channels, 'calibrated', 'verification', 0, 730)
        repeat = initial_units(truth, channels, 'calibrated', 'verification', 0, 730)
        self.assertEqual(first[0]['state'].remaining_u, repeat[0]['state'].remaining_u)
        auxiliary = RenewalExponential([90, 0, 0, 0, 0, 1, 0], 1).exponential()
        self.assertNotEqual(first[0]['state'].remaining_u, auxiliary)


if __name__ == '__main__':
    unittest.main()
