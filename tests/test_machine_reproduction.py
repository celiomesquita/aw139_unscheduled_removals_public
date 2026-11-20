"""T17b boundary: tolerate old-host floats, never integer/decision changes."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from machine_reproduction import compare_old_frame, compare_old_json, old_digest_matches, compare_hierarchical_frame, compare_hierarchical_json, compare_author_closure_frame


class TestOldHostComparison(unittest.TestCase):
    def test_one_ulp_is_allowed_only_for_float_columns(self):
        old = pd.DataFrame({'log_score': [.5], 'count': [2], 'decision': [False]})
        new = old.copy()
        new.loc[0, 'log_score'] = np.nextafter(.5, 1.)
        self.assertGreater(compare_old_frame(new, old), 0.)
        for field, value in [('count', 3), ('decision', True)]:
            changed = new.copy()
            changed.loc[0, field] = value
            with self.assertRaises(AssertionError):
                compare_old_frame(changed, old)

    def test_relative_limit_uses_historical_magnitude(self):
        stats = {}
        compare_old_frame(pd.DataFrame({'x': [1e6 + .5]}), pd.DataFrame({'x': [1e6]}), stats)
        self.assertAlmostEqual(stats['x']['max_ratio'], .5/(1e-8+1.))
        with self.assertRaises(AssertionError):
            compare_old_frame(pd.DataFrame({'x': [1e6 + 2.]}), pd.DataFrame({'x': [1e6]}))

    def test_tiny_sign_change_in_decision_bound_is_rejected(self):
        with self.assertRaises(AssertionError):
            compare_old_frame(pd.DataFrame({'ci_lo': [1e-16]}), pd.DataFrame({'ci_lo': [-1e-16]}))
        with self.assertRaises(AssertionError):
            compare_old_frame(pd.DataFrame({'delta_log': [0.]}), pd.DataFrame({'delta_log': [-1e-16]}))

    def test_absolute_limit_at_zero_and_nan_mask(self):
        compare_old_frame(pd.DataFrame({'x': [1e-8]}), pd.DataFrame({'x': [0.]}))
        with self.assertRaises(AssertionError):
            compare_old_frame(pd.DataFrame({'x': [1.01e-8]}), pd.DataFrame({'x': [0.]}))
        with self.assertRaises(AssertionError):
            compare_old_frame(pd.DataFrame({'x': [0.]}), pd.DataFrame({'x': [np.nan]}))

    def test_all_interval_bound_names_keep_exact_sign(self):
        for column in ('beta_lo', 'beta_hi', 'exact_beta_lo', 'gap_lower_hours'):
            with self.assertRaises(AssertionError):
                compare_old_frame(pd.DataFrame({column: [1e-16]}),
                                  pd.DataFrame({column: [-1e-16]}))

    def test_json_counts_hashes_and_decisions_remain_exact(self):
        self.assertLessEqual(compare_old_json({'x': .5 + 1e-16}, {'x': .5}), 1e-12)
        for a, b in [(True, False), (3, 2), ('hash1', 'hash2')]:
            with self.assertRaises(AssertionError):
                compare_old_json(a, b)

    def test_input_hash_accepts_only_original_or_crlf(self):
        import hashlib
        expected = hashlib.sha256(b'a\r\n').hexdigest()
        self.assertTrue(old_digest_matches(b'a\n', expected))
        self.assertFalse(old_digest_matches(b'b\n', expected))


class TestHierarchicalTransfer(unittest.TestCase):
    def test_scientific_absolute_limit_not_relative(self):
        for difference in (9e-5, 1.01e-4):
            actual = pd.DataFrame({'delta_log': [.01 + difference]})
            expected = pd.DataFrame({'delta_log': [.01]})
            if difference < 1e-4:
                compare_hierarchical_frame(actual, expected, 'intervals.csv')
            else:
                with self.assertRaises(AssertionError):
                    compare_hierarchical_frame(actual, expected, 'intervals.csv')

    def test_pn_delta_reported_aggregate_delta_bounded(self):
        old = pd.DataFrame({'pn': ['aggregate', 'PN'], 'delta_log': [.01, -.24]})
        new = old.copy()
        new.loc[1, 'delta_log'] = -.20
        report = {}
        compare_hierarchical_frame(new, old, 'intervals.csv', report)
        self.assertEqual(report['delta_log']['pn_bound_max_ratio'], None)
        self.assertEqual(report['delta_log']['aggregate_max_ratio'], 0.)
        new.loc[0, 'delta_log'] = .0102
        with self.assertRaises(AssertionError):
            compare_hierarchical_frame(new, old, 'intervals.csv')

    def test_pn_bounds_half_margin_including_near_zero(self):
        for historical, current, accepted in [(.5, .75, True), (.5, .751, False),
                (1e-8, 1.4e-8, True), (1e-8, 1.6e-8, False), (0., 0., True), (0., 1e-12, False)]:
            old = pd.DataFrame({'pn': ['PN'], 'ci_lo': [historical]})
            new = pd.DataFrame({'pn': ['PN'], 'ci_lo': [current]})
            if accepted:
                compare_hierarchical_frame(new, old, 'intervals.csv')
            else:
                with self.assertRaises(AssertionError):
                    compare_hierarchical_frame(new, old, 'intervals.csv')

    def test_aggregate_bound_uses_absolute_not_its_margin(self):
        old = pd.DataFrame({'pn': ['aggregate'], 'ci_lo': [.001]})
        with self.assertRaises(AssertionError):
            compare_hierarchical_frame(pd.DataFrame({'pn': ['aggregate'], 'ci_lo': [.0012]}),
                                      old, 'intervals.csv')

    def test_interval_sign_change_blocks_even_within_limit(self):
        with self.assertRaises(AssertionError):
            compare_hierarchical_frame(pd.DataFrame({'ci_lo': [1e-9]}),
                                      pd.DataFrame({'ci_lo': [-1e-9]}), 'intervals.csv')

    def test_calibration_observed_only_reported_but_n_exact(self):
        old = pd.DataFrame({'observed': [2], 'n': [10], 'expected': [2.]})
        new = old.assign(observed=3, expected=3.)
        report = {}
        compare_hierarchical_frame(new, old, 'calibration_principal.csv', report)
        self.assertEqual(report['observed']['max_abs_difference'], 1)
        self.assertEqual(report['expected']['mode'], 'reported_only')
        with self.assertRaises(AssertionError):
            compare_hierarchical_frame(new.assign(n=11), old, 'calibration_principal.csv')
        with self.assertRaises(AssertionError):
            compare_hierarchical_frame(new, old, 'counts_principal.csv')

    def test_optimizer_evaluations_reported_convergence_exact(self):
        old = pd.DataFrame({'evaluations': [12], 'successful_attempts': [4], 'attempts': [5],
                            'converged': [True], 'boundary': [False], 'zero_variance': [False], 'beta': [2.]})
        new = old.assign(evaluations=14, successful_attempts=5, beta=2.1)
        compare_hierarchical_frame(new, old, 'hyperparameters.csv')
        for field, value in [('converged', False), ('attempts', 6), ('boundary', True), ('zero_variance', True)]:
            with self.assertRaises(AssertionError):
                compare_hierarchical_frame(new.assign(**{field: value}), old, 'hyperparameters.csv')
        compare_hierarchical_json({'successful_attempts': 5}, {'successful_attempts': 4})

    def test_json_decisions_counts_and_fallbacks_exact(self):
        for field, old, new in [('pn_rejected', True, False), ('predictions', 10, 11),
                                ('hW_fallback', .25, .26)]:
            with self.assertRaises(AssertionError):
                compare_hierarchical_json({field: new}, {field: old})
        compare_hierarchical_json({'delta_log': .01005}, {'delta_log': .01})

    def test_a5_keeps_T17c(self):
        old = pd.DataFrame({'prediction': [.1]})
        new = pd.DataFrame({'prediction': [.10001]})
        compare_hierarchical_frame(new, old, 'predictions.csv')
        with self.assertRaises(AssertionError):
            compare_old_frame(new, old)


class TestAuthorClosure(unittest.TestCase):
    def test_other_host_diagnostics_are_only_reported(self):
        old = pd.DataFrame({'zero_variance':[True], 'boundary':[False], 'converged':[True],
                            'n':[1], 'objective':[1.], 'delta_log':[.01]})
        new = old.assign(zero_variance=False,boundary=True,converged=False,n=3,objective=3.,delta_log=2.)
        report = {}
        compare_author_closure_frame(new,old,'hyperparameters_principal.csv',report)
        self.assertEqual(report['zero_variance']['changed_values'],1)
        self.assertEqual(report['n']['changed_values'],1)

    def test_only_outcomes_block_in_decision_table(self):
        old = pd.DataFrame({'variant':['principal'],'aggregation':['aircraft'],
                            'criterion':['K2-A4'],'outcome':['favoravel'],'predictions':[10]})
        compare_author_closure_frame(old.assign(predictions=20),old,'decision_principal.csv')
        with self.assertRaises(AssertionError):
            compare_author_closure_frame(old.assign(outcome='nula'),old,'decision_principal.csv')

    def test_interval_sign_blocks_without_numerical_limit(self):
        old = pd.DataFrame({'variant':['principal'],'aggregation':['aircraft'],
            'criterion':['K2-A4'],'pn':['aggregate'],'delta_log':[.01],
            'ci_lo':[.001],'ci_hi':[.1],'simultaneous_lo':[.001],'simultaneous_hi':[.1]})
        compare_author_closure_frame(old.assign(delta_log=4.,ci_lo=.2),old,'intervals_principal.csv')
        with self.assertRaises(AssertionError):
            compare_author_closure_frame(old.assign(ci_lo=-1e-20),old,'intervals_principal.csv')


if __name__ == '__main__':
    unittest.main()
