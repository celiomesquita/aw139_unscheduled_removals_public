"""A16 fixed-cell inference, stopping and seed separation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
from a16_power import (atomic_json, calibration_failure, cells, rejected,
                       summarize_cell, wilson, write_gzip_csv)


def replica_record(replicate, hit=False, status='ok'):
    value = dict(status=status)
    if status == 'ok':
        value['criteria'] = {'K2-idade': dict(aggregate_rejected=hit,
            family_rejected=hit, pn_rejected={'PN': hit})}
    return dict(replicate=replicate, variants={v: copy.deepcopy(value) for v in ('principal', 'realized_fh')})


class TestA16Power(unittest.TestCase):
    def test_nine_cells_null_first_with_stable_seed_ids(self):
        grid = cells()
        self.assertEqual(len(grid), 9)
        self.assertEqual([c['level'] for c in grid[:3]], ['null'] * 3)
        self.assertEqual([c['copies'] for c in grid[:3]], [1, 2, 4])
        self.assertEqual([c['seed_cell'] for c in grid[:3]], [3, 4, 5])
        self.assertEqual(len({c['seed_cell'] for c in grid}), 9)

    def test_rejections_use_aggregate_ci_and_PN_simultaneous_limits(self):
        ci = pd.DataFrame({'pn': ['aggregate', 'PN'], 'delta_log': [0., .1],
                           'ci_lo': [-.1, .01], 'simultaneous_lo': [-.1, -.02]})
        self.assertFalse(rejected(ci)['aggregate_rejected'])
        self.assertFalse(rejected(ci)['family_rejected'])
        ci.loc[1, 'simultaneous_lo'] = .01
        self.assertTrue(rejected(ci)['family_rejected'])

    def test_no_interim_stop_and_strict_point_ten_threshold(self):
        cell = cells()[0]
        with self.assertRaises(ValueError):
            summarize_cell(cell, [replica_record(0, True)], ['PN'], 200)
        at_nominal = [replica_record(r, r < 20) for r in range(200)]
        self.assertFalse(calibration_failure(summarize_cell(cell, at_nominal, ['PN'], 200)))
        over = [replica_record(r, r < 21) for r in range(200)]
        self.assertTrue(calibration_failure(summarize_cell(cell, over, ['PN'], 200)))

    def test_failures_stay_in_denominator_and_have_explicit_bounds(self):
        records = [replica_record(r, r < 5, 'failed' if r >= 190 else 'ok') for r in range(200)]
        summary = summarize_cell(cells()[0], records, ['PN'], 200)
        row = summary.iloc[0]
        self.assertEqual(row.failures, 10)
        self.assertEqual(row.frequency, .025)
        self.assertEqual(row.failure_upper, .075)
        all_failed = [replica_record(r, status='failed') for r in range(200)]
        self.assertTrue(calibration_failure(summarize_cell(cells()[0], all_failed, ['PN'], 200)))

    def test_wilson_and_mc_interval_boundaries(self):
        lo, hi = wilson(0, 200)
        self.assertAlmostEqual(lo, 0, places=15)
        self.assertGreater(hi, 0)
        lo, hi = wilson(100, 200)
        self.assertAlmostEqual(lo + hi, 1.)
        self.assertLess(lo, .5)
        self.assertGreater(hi, .5)

    def test_atomic_checkpoint_and_gzip_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'summary.json'
            atomic_json(path, {'b': 2, 'a': 1})
            first = path.read_bytes()
            atomic_json(path, {'a': 1, 'b': 2})
            self.assertEqual(first, path.read_bytes())
            self.assertEqual(json.loads(first), {'a': 1, 'b': 2})
            self.assertFalse(path.with_suffix('.json.tmp').exists())
            frame = pd.DataFrame({'x': [1., 2.]})
            write_gzip_csv(frame, folder / 'a.csv.gz')
            write_gzip_csv(frame, folder / 'b.csv.gz')
            self.assertEqual((folder / 'a.csv.gz').read_bytes(), (folder / 'b.csv.gz').read_bytes())


if __name__ == '__main__':
    unittest.main()
