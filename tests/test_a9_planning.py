from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_planning import cost_arcs, optimise_visit_plan, refined_arcs


class TestPolicyPlanning(unittest.TestCase):
    def test_constant_hazard_never_pays_for_uninformative_prevention(self):
        unit = dict(unit='SIM-0', age=12., daily=[1.] * 6, visits=[2., 4.],
                    beta=1., eta=2., nu=.1, r=5., terminal_daily=[1.], mh=1.)
        plan, diagnostic = optimise_visit_plan([unit], [1., 1.])
        self.assertEqual(plan['SIM-0'], ())
        self.assertTrue(diagnostic['proven_optimal'])
        self.assertAlmostEqual(diagnostic['selected_expected_cost'],
                               6 * (5 / 2 + .1) + (5 / 2 + .1) / (.5 + .1), places=8)

    def test_weibull_arcs_are_refined_before_optimisation(self):
        arcs, history = refined_arcs('SIM-1', 2., [1.] * 6, [2., 4.],
                                     2., 4., .1, 5., [1.])
        self.assertGreater(len(history), 2)
        self.assertLess(history[-1]['step_days'], history[0]['step_days'])
        self.assertEqual(len(arcs), 6)
        self.assertLess(history[-1]['probability_mass_error'], 1e-7)

    def test_reused_renewal_matrix_does_not_reuse_the_units_current_age(self):
        cache = {}
        first, _ = cost_arcs('A', 0., [1.] * 6, [2., 4.], 2., 4., .1, 5., [1.], model_cache=cache)
        cached, _ = cost_arcs('B', 10., [1.] * 6, [2., 4.], 2., 4., .1, 5., [1.], model_cache=cache)
        independent, _ = cost_arcs('B', 10., [1.] * 6, [2., 4.], 2., 4., .1, 5., [1.])
        self.assertEqual([a.cost for a in cached], [a.cost for a in independent])
        self.assertNotEqual(first[0].cost, cached[0].cost)
        self.assertEqual(len(cache), 1)


if __name__ == '__main__':
    unittest.main()
