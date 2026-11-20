import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'analysis'))
from a9_static_fast import FastCalendarRenewal, exhaustive_threshold

spec = importlib.util.spec_from_file_location('static_before012',
    ROOT / 'analysis/audit/amendment012/before_optimisation/analysis/a9_static.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


class TestEquivalentStaticOptimisation(unittest.TestCase):
    def test_global_search_retains_threshold_and_rate(self):
        for days in (3, 7, 14):
            contexts = [dict(daily=[1 + (i % 3) for i in range(days)], visits=[0, days - 1]),
                        dict(daily=[0.] * days, visits=[0])]
            for subdivision in (1, 2):
                old_age, old = legacy.exhaustive_threshold(contexts, 2., 10., .05, 5., subdivision)
                new_age, new = exhaustive_threshold(contexts, 2., 10., .05, 5., subdivision)
                self.assertEqual(new_age, old_age)
                self.assertEqual(new['candidate_breakpoints'], old['candidate_breakpoints'])
                self.assertAlmostEqual(new['expected_rate_variable_groups'],
                                       old['expected_rate_variable_groups'], delta=1e-9)

    def test_incremental_probability_and_inverse_retain_reference(self):
        daily = [1 + (j % 4) / 4 for j in range(28)]
        before = legacy.CalendarRenewal(daily, [0, 7, 17, 25], 2., 20., .05, 5.)
        after = FastCalendarRenewal(daily, [0, 7, 17, 25], 2., 20., .05, 5.)
        for i in range(1000):
            phase = i % after.n
            if not np.isfinite(before.next_breakpoint(phase)):
                continue
            before.extend(phase)
            after.extend(phase)
            if i % 64 == 0:
                np.testing.assert_allclose(after.P, before.P, rtol=0, atol=1e-11)
                np.testing.assert_allclose(after.stationary, before.stationary, rtol=0, atol=1e-9)
                self.assertAlmostEqual(after.rate(), before.rate(), delta=1e-9)
        self.assertLess(after.full_refactors, before.updates // 128 + 2)

    def test_analytic_and_survival_kernels_match_reference(self):
        for nu, eta in ((0., 20.), (.01, 1000.)):
            before = legacy.CalendarRenewal([0., 1., 2., 0., 1., 2., 1.], [0, 3, 6],
                                            2., eta, nu, 5.)
            after = FastCalendarRenewal([0., 1., 2., 0., 1., 2., 1.], [0, 3, 6],
                                        2., eta, nu, 5.)
            expected = ('analytic_no_competing' if nu == 0 else
                        'survival_integral_with_exact_zero_clock')
            self.assertIn(expected, after.kernel_kinds)
            for old, new in zip(before.rows, after.rows):
                np.testing.assert_allclose(new['left'], old['left'], rtol=0, atol=1e-11)
                np.testing.assert_allclose(new['right'], old['right'], rtol=0, atol=1e-11)
            np.testing.assert_allclose(after.P, before.P, rtol=0, atol=1e-10)
            self.assertAlmostEqual(after.rate(), before.rate(), delta=1e-9)

    def test_stiff_clock_retains_reference_quadrature(self):
        before = legacy.CalendarRenewal([1.], [0], 2., 1., .1, 5.)
        after = FastCalendarRenewal([1.], [0], 2., 1., .1, 5.)
        self.assertIn('reference_fallback', after.kernel_kinds)
        self.assertAlmostEqual(after.rate(), before.rate(), places=12)

    def test_complete_analytic_kernel_search_retains_the_selected_age(self):
        contexts = [dict(daily=[0., 1., 2., 0., 1., 2., 1.], visits=[0, 3, 6])]
        for beta in (1.5, 2., 3.):
            old_age, old = legacy.exhaustive_threshold(contexts, beta, 20., 0., 5.)
            new_age, new = exhaustive_threshold(contexts, beta, 20., 0., 5.)
            self.assertEqual(old_age, new_age)
            self.assertAlmostEqual(old['expected_rate_variable_groups'],
                                   new['expected_rate_variable_groups'], delta=1e-9)


if __name__ == '__main__':
    unittest.main()
