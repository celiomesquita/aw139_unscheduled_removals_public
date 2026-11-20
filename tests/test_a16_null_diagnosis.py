"""T13 aggregation/exclusion must match the original scientific estimand."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
from a16_null_diagnosis import contributions, focus_mask
from a5_validation import cluster_means, log_score


class TestNullDiagnosis(unittest.TestCase):
    def test_focus_excludes_only_the_specified_aircraft_origin_and_all_copies(self):
        frame = pd.DataFrame({'aircraft': ['AC-22', 'AC-22-R01', 'AC-22-R04', 'AC-02-R01', 'AC-22-R01'],
            'origin': ['2025-12-01'] * 4 + ['2025-11-01']})
        self.assertEqual(focus_mask(frame).tolist(), [True, True, True, False, False])

    def test_aircraft_origin_contributions_reconcile_unequal_unit_counts(self):
        frame = pd.DataFrame({'pn': ['PN'] * 7, 'aircraft': ['AC1'] * 5 + ['AC2'] * 2,
            'origin': ['2025-01-01'] * 3 + ['2025-02-01'] * 4,
            'horizon': [1, 1, 2, 1, 2, 1, 2], 'y': [0, 1, 1, 0, 0, 1, 0],
            'w_selected': [.1, .2, .3, .2, .4, .5, .2], 'e_selected': [.2] * 7})
        pn, detail, aggregate, point = contributions(frame)
        expected = cluster_means(frame, log_score(frame.y, frame.w_selected) -
                                 log_score(frame.y, frame.e_selected)).mean()
        self.assertAlmostEqual(point, expected)
        self.assertAlmostEqual(sum(row[-1] for row in detail), expected)
        self.assertAlmostEqual(sum(row[-1] for row in aggregate), expected)
        self.assertAlmostEqual(pn[0]['delta_log'], expected)


if __name__ == '__main__':
    unittest.main()
