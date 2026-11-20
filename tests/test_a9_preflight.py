import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_preflight import preventive_mh


class TestPreventiveMH(unittest.TestCase):
    def inputs(self):
        domain = pd.DataFrame({'pn': ['PN-1']})
        summary = pd.DataFrame([
            dict(pn='PN-1', aggregation='row_sum', cohort='single_document',
                 documents=0, n_observed=0, median=float('nan'), q1=float('nan'), q3=float('nan')),
            dict(pn='PN-1', aggregation='row_sum', cohort='all_equal_share',
                 documents=5, n_observed=5, median=9., q1=7., q3=11.)])
        config = pd.DataFrame(columns=['parametro', 'valor_central'])
        return domain, summary, config

    def test_shared_document_proxy_does_not_replace_missing_mh(self):
        result = preventive_mh(*self.inputs())[0]
        self.assertFalse(result['available'])
        self.assertIsNone(result['preventive_mh'])

    def test_available_coefficient_must_match_configuration(self):
        domain, summary, config = self.inputs()
        summary.loc[0, ['documents', 'n_observed', 'median', 'q1', 'q3']] = [2, 2, 4., 3., 5.]
        config.loc[0] = ['mh_row_sum_PN-1', '4.0']
        self.assertEqual(preventive_mh(domain, summary, config)[0]['preventive_mh'], 4.)
        config.loc[0, 'valor_central'] = '8.0'
        with self.assertRaisesRegex(ValueError, 'differs from T4'):
            preventive_mh(domain, summary, config)


if __name__ == '__main__':
    unittest.main()
