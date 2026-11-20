"""Checks for common-measure likelihood and scale selection in A2."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'analysis'))
from time_scales import daily_nll, fit_daily, select_scale, cycle_clock


class TestTimeScales(unittest.TestCase):
    def test_exponential_interval_probability(self):
        value = daily_nll(np.log([1., 10.]), np.array([2., 4.]),
                          np.array([3., 5.]), np.array([True, False]))
        self.assertAlmostEqual(value, -np.log(np.exp(-.2)-np.exp(-.3)) + .5)

    def test_units_do_not_change_likelihood(self):
        lo, hi, event = np.array([1., 4.]), np.array([2., 5.]), np.array([True, False])
        self.assertAlmostEqual(daily_nll(np.log([2., 10.]), lo, hi, event),
                               daily_nll(np.log([2., 240.]), lo*24, hi*24, event))

    def test_recover_weibull_with_daily_rounding_and_censoring(self):
        rng = np.random.default_rng(89)
        life = 100 * rng.weibull(2., 4000)
        event = life <= 120
        upper = np.minimum(np.ceil(life), 120)
        result = fit_daily(np.maximum(upper-1, 0), upper, event)
        self.assertTrue(result['converged'])
        self.assertAlmostEqual(result['beta'], 2., delta=.12)
        self.assertAlmostEqual(result['eta'], 100., delta=4.)

    def test_zero_exposure_failure_is_not_fitted(self):
        self.assertFalse(fit_daily([0, 2], [0, 3], [1, 0])['converged'])

    def test_selection_margin_and_convergence(self):
        scores = pd.DataFrame(dict(scale=['FH', 'calendar', 'takeoffs'],
                                   aic=[100., 98.1, 70.], converged=[True, True, False]))
        self.assertEqual(select_scale(scores), 'FH')
        scores.loc[1, 'aic'] = 98.
        self.assertEqual(select_scale(scores), 'calendar')

    def test_missing_counter_is_preserved(self):
        h = pd.DataFrame({'Flight Date': ['01/01/2024', '02/01/2024'],
                          'Aircraft #': ['AC-01']*2, 'Take Off': [2., np.nan]})
        clock, missing = cycle_clock(h)
        self.assertEqual(clock.loc['2024-01-02', 'AC-01'], 2.)
        self.assertEqual(missing.loc['2024-01-02', 'AC-01'], 1)


if __name__ == '__main__':
    unittest.main()
