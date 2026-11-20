import sys
from pathlib import Path
import unittest

import numpy as np
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_renewal import RenewalCosts, first_event_weights, terminal_cycle


class TestA9Renewal(unittest.TestCase):
    def test_poisson_counts_include_repeated_events_and_terminal_cycle(self):
        times = np.arange(9.)
        costs = RenewalCosts(times, 2 * times, 1., 1., 1., 5., order=32)
        # 24 expected renewals in 8 days; not a single-event probability.
        value, _ = costs.current(3., 8)
        self.assertAlmostEqual(value, (5 * 2 + 1) * 8, places=9)
        value, _ = costs.current(3., 8, [2.])
        self.assertAlmostEqual(value, 88 + 11 / 3, places=9)

    def test_known_time_varying_exponential_clock(self):
        times = np.arange(6.)
        clock = np.r_[0., np.cumsum([0., 5., 0., 2., 1.])]
        costs = RenewalCosts(times, clock, 1., 4., .2, 3., order=32)
        value, _ = costs.current(2., 5)
        self.assertAlmostEqual(value, 3 * 8 / 4 + .2 * 5, places=9)

    def test_singular_weibull_density_integrates_to_probability(self):
        for beta in (.4, 1., 3.):
            u, c, left, right = first_event_weights(np.arange(6.), np.arange(6.),
                                                    0., beta, 2., .1, order=48)
            expected = 1 - np.exp(-(5 / 2) ** beta - .5)
            self.assertAlmostEqual(float((u + c).sum()), expected, places=9)
            np.testing.assert_allclose(left + right, u + c, atol=1e-14)

    def test_terminal_cycle_matches_independent_competing_integral(self):
        age, beta, eta, nu, r = 2., 2., 4., .1, 5.
        pc = nu * quad(lambda t: np.exp(-(((age + t) / eta) ** beta -
                                           (age / eta) ** beta) - nu * t), 0, np.inf)[0]
        value, bound = terminal_cycle([age], [1.], beta, eta, nu, r)
        self.assertAlmostEqual(value[0], r - (r - 1) * pc, places=8)
        self.assertLess(bound, 1e-9)

    def test_zero_clock_and_zero_time(self):
        costs = RenewalCosts([0., 1.], [0., 0.], 2., 4., 0., 5.)
        self.assertEqual(costs.current(3., 1)[0], 0.)
        self.assertEqual(costs.current(3., 0, [0.])[0], 0.)
        self.assertEqual(terminal_cycle([3.], [0.], 2., 4., .1, 5.)[0][0], 1.)

    def test_terminal_quadrature_handles_singular_initial_density(self):
        beta, eta, nu, r = .4, 2., .1, 5.
        expected_pc = quad(lambda u: nu / beta * u ** (1 / beta - 1) *
            np.exp(-u / eta ** beta - nu * u ** (1 / beta)), 0, np.inf,
            epsabs=1e-11, epsrel=1e-11)[0]
        diagnostic = {}
        value, bound = terminal_cycle([0.], [1., 2.], beta, eta, nu, r, diagnostics=diagnostic)
        # Reference below uses a constant clock; retain that independently computable case.
        value, bound = terminal_cycle([0.], [1.], beta, eta, nu, r, diagnostics=diagnostic)
        self.assertAlmostEqual(value[0], r - (r - 1) * expected_pc, places=7)
        self.assertGreater(diagnostic['order'], 8)
        self.assertLess(bound, 1e-9)


if __name__ == '__main__':
    unittest.main()
