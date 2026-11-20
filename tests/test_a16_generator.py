"""Tests before real-clock generator calibration; no A4/A5 fits."""
import itertools
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import gamma
from scipy.stats import binom

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
from a16_generator import (colour_channels, event_observed, inverse_clock,
                          preserve_mean, renewal_path, union_intervals)


class TestA16Generator(unittest.TestCase):
    def test_inverse_clock_interpolates_and_handles_no_future_exposure(self):
        curve = np.array([0., 0., 2., 2., 6.])
        self.assertEqual(inverse_clock(curve, 1), 1.5)
        self.assertEqual(inverse_clock(curve, 4), 3.5)
        self.assertEqual(inverse_clock(curve, 7), np.inf)

    def test_zero_clock_and_late_entry_preserve_censor(self):
        rows = list(renewal_path(np.zeros(11), 2., 10., 2., 1., 0.,
            np.random.default_rng(7), np.random.default_rng(8)))
        self.assertEqual(rows, [(2., 10., 0, 0.)])

    def test_competing_event_renews_unit_without_unplanned_exposure(self):
        rows = list(renewal_path(np.zeros(11), 0., 10., 2., 1., 2.,
            np.random.default_rng(7), np.random.default_rng(8)))
        self.assertGreater(len(rows), 2)
        self.assertTrue(all(r[2] == 2 for r in rows[:-1]))
        self.assertEqual(rows[-1][2], 0)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(rows, rows[1:])))

    def test_multiple_renewals_per_day_and_deterministic_replay(self):
        def run():
            return list(renewal_path(np.array([0., 10.]), 0., 1., 1., .2, 0.,
                np.random.default_rng(11), np.random.default_rng(12)))
        first = run()
        self.assertEqual(first, run())
        self.assertGreater(sum(r[2] == 1 for r in first), 10)
        self.assertEqual(first[-1][1], 1.)

    def test_known_weibull_quantiles_in_precomputed_99_percent_bands(self):
        # Fixed n, probabilities and binomial bands before looking at generated ages.
        n = 20000
        probabilities = (.1, .5, .9)
        bounds = [binom.interval(.99, n, q) for q in probabilities]
        for beta in (1., 2.5):
            eta = 20.
            path = renewal_path(np.array([0., 1e7]), 0., 1., beta, eta, 0.,
                np.random.default_rng(20261112), np.random.default_rng(8))
            rows = list(itertools.islice(path, n))
            self.assertEqual(len(rows), n)
            self.assertTrue(all(r[2] == 1 for r in rows))
            ages = np.array([r[3] for r in rows])
            for q, (lo, hi) in zip(probabilities, bounds):
                theoretical = eta * (-np.log1p(-q)) ** (1 / beta)
                count = np.count_nonzero(ages <= theoretical)
                self.assertGreaterEqual(count, lo)
                self.assertLessEqual(count, hi)

    def test_mean_preserved_for_all_beta_levels(self):
        beta, eta = np.array([1.4, 2., 3.]), np.array([100., 200., 300.])
        for new in (np.ones(3), beta, 1 + 1.5 * (beta - 1)):
            adjusted = preserve_mean(beta, eta, new)
            np.testing.assert_allclose(adjusted * gamma(1 + 1 / new), eta * gamma(1 + 1 / beta),
                                       rtol=1e-15)

    def test_channel_colouring_reuses_lowest_free_channel(self):
        base = pd.Timestamp('2024-01-01')
        frame = pd.DataFrame({'Aircraft #': ['AC-01'] * 4, 'Part #': ['PN'] * 4,
            'att': [base + pd.Timedelta(days=d) for d in [0, 1, 3, 6]],
            'rem': [base + pd.Timedelta(days=d) for d in [3, 5, 6, 8]],
            'real_id': [0, 1, 2, 3]})
        coloured = colour_channels(frame).set_index('real_id')
        self.assertEqual(coloured.channel.to_dict(), {0: 0, 1: 1, 2: 0, 3: 0})
        self.assertEqual(len(coloured), len(frame))

    def test_observation_union_does_not_double_exposure_or_count_gaps(self):
        self.assertEqual(union_intervals([(2, 2)]), [])
        intervals = union_intervals([(3, 5), (0, 3), (7, 9)])
        self.assertEqual(intervals, [(0, 5), (7, 9)])
        self.assertTrue(event_observed(5, intervals))
        self.assertFalse(event_observed(6, intervals))
        self.assertFalse(event_observed(7, intervals))
        self.assertTrue(event_observed(8, intervals))


if __name__ == '__main__':
    unittest.main()
