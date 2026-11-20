from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.integrate import quad
from scipy.special import gamma

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_static import CalendarRenewal, exhaustive_threshold


class TestStaticAgeCalibration(unittest.TestCase):
    def test_one_phase_matches_analytical_cycle_ratio(self):
        beta, eta, r = 2., 4., 5.
        contexts = [dict(daily=[1.], visits=[0.], weight=1.)]
        threshold, diagnostic = exhaustive_threshold(contexts, beta, eta, 0., r)
        theoretical = []
        for t in range(1, 50):
            s = np.exp(-(t / eta) ** beta)
            denominator = quad(lambda x: np.exp(-(x / eta) ** beta), 0, t)[0]
            theoretical.append(((r * (1 - s) + s) / denominator, t))
        expected, age = min(theoretical)
        self.assertAlmostEqual(diagnostic['expected_rate_variable_groups'], expected, places=8)
        self.assertEqual(int(np.ceil(threshold)), age)
        self.assertAlmostEqual(diagnostic['no_preventive_rate_variable_groups'],
                               r / (eta * gamma(1 + 1 / beta)), places=7)

    def test_rank_one_updates_match_independent_refactor(self):
        model = CalendarRenewal([1., .5, 2.], [0., 2.], 2., 4., .1, 5.)
        for phase in (0, 1, 2, 0, 1, 0):
            model.extend(phase)
            incremental = model.stationary.copy()
            rate = model.rate()
            model.refactor()
            np.testing.assert_allclose(incremental, model.stationary, atol=1e-10)
            self.assertAlmostEqual(rate, model.rate(), places=10)

    def test_nonageing_policy_can_remain_corrective(self):
        age, diagnostic = exhaustive_threshold([dict(daily=[1.], visits=[0.])], 1., 4., .1, 5.)
        self.assertTrue(np.isinf(age))
        self.assertTrue(diagnostic['global_discrete_search'])

    def test_zero_exposure_group_does_not_force_an_unnecessary_preventive(self):
        contexts = [dict(daily=[1.], visits=[0.]), dict(daily=[0.], visits=[0.])]
        age, diagnostic = exhaustive_threshold(contexts, 2., 1., 0., 10.)
        self.assertGreater(age, 0.)
        self.assertLessEqual(age, 1.)
        survival = np.exp(-1.)
        duration = quad(lambda t: np.exp(-t * t), 0, 1)[0]
        self.assertAlmostEqual(diagnostic['expected_rate_variable_groups'],
                               (10 * (1 - survival) + survival) / duration, places=8)


if __name__ == '__main__':
    unittest.main()
