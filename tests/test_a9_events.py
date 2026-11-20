from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_events import UnitState, eta_factor, hazard_increment


class TestPolicyEvents(unittest.TestCase):
    def test_eta_jump_preserves_accumulated_risk(self):
        unit = UnitState((9, 0, 0, 0, 0), 2., 0.)
        unit.remaining_u = 2.
        self.assertEqual(unit.advance(1., 1., 2., 2.), [])
        self.assertAlmostEqual(unit.age, 1.)
        self.assertAlmostEqual(unit.remaining_u, 1.75)
        events = unit.advance(2., 1., 1., 1.)
        self.assertAlmostEqual(events[0]['end'], np.sqrt(2.75), places=9)

    def test_gradual_hazard_matches_independent_quadrature(self):
        expected = quad(lambda t: 2.5 * 2 * (3 + 2 * t) ** 1.5 /
                         (10 - 3 * t) ** 2.5, 0, 1)[0]
        self.assertAlmostEqual(hazard_increment(3., 2., 1., 2.5, 10., 7.), expected, places=12)
        self.assertEqual(eta_factor('wheels', 'B-eta', 20., 10., 30.), 1.)
        self.assertAlmostEqual(eta_factor('rotor', 'B-gradual', 20., 10., 30.), .85)

    def test_many_events_and_common_random_numbers(self):
        first, second = UnitState((9, 1, 0, 0), 1., 0.), UnitState((9, 1, 0, 0), 1., 0.)
        a = first.advance(1., 1., .02, .02)
        b = second.advance(1., 1., .02, .02)
        self.assertEqual(a, b)
        self.assertGreater(len(a), 1)
        other = UnitState((9, 1, 0, 1), 1., 0.)
        self.assertNotEqual(a, other.advance(1., 1., .02, .02))

    def test_zero_clock_retains_unscheduled_risk(self):
        unit = UnitState((9, 2, 0), 2., 0.)
        threshold = unit.remaining_u
        self.assertEqual(unit.advance(30., 0., 5., 5.), [])
        self.assertEqual(unit.remaining_u, threshold)
        self.assertEqual(unit.age, 0.)


if __name__ == '__main__':
    unittest.main()
