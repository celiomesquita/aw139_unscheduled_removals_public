"""Likelihood recovery and protection against unsupported inspection bounds."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'analysis'))
from inspection_censoring import construct_intervals, fit_mixed, mixed_nll
from feasibility import weibull_fit
from time_scales import compare


class TestInspectionCensoring(unittest.TestCase):
    def test_exact_likelihood_matches_existing_mle(self):
        rng = np.random.default_rng(81)
        life = 500*rng.weibull(2., 1000)
        upper, event = np.minimum(life, 600), life <= 600
        result = fit_mixed(upper, upper, event, np.zeros(len(life), bool))
        beta, eta, *_ = weibull_fit(upper, event, np.zeros(len(life)))
        self.assertTrue(result['converged'])
        self.assertAlmostEqual(result['beta'], beta, delta=.001)
        self.assertAlmostEqual(result['eta'], eta, delta=.05)

    def test_interval_sample_recovers_parameters(self):
        rng = np.random.default_rng(82)
        life = 500*rng.weibull(2., 4000)
        event = life <= 800
        upper = np.minimum(np.ceil(life/100)*100, 800)
        lower = np.maximum(upper-100, 0)
        result = fit_mixed(lower, upper, event, event)
        self.assertTrue(result['converged'])
        self.assertAlmostEqual(result['beta'], 2., delta=.12)
        self.assertAlmostEqual(result['eta'], 500., delta=15)

    def test_mixed_likelihood_analytic(self):
        value = mixed_nll(np.log([1., 10.]), np.array([2., 4., 5.]),
                          np.array([3., 4., 5.]), np.array([True, True, False]),
                          np.array([True, False, False]))
        expected = -np.log(np.exp(-.2)-np.exp(-.3)) + np.log(10)+.4+.5
        self.assertAlmostEqual(value, expected)

    def fixture(self):
        sp = pd.DataFrame({'Part #':['3G6230A00833'], 'Serial #':['S1'],
                           'Aircraft #':['AC-01'], 'ATA #':[6200.],
                           'att':[pd.Timestamp('2024-01-01')],
                           'rem':[pd.Timestamp('2024-02-01')], 'event':[1]})
        r = sp.copy()
        r['Source Doc #'] = 'D2'
        t = pd.DataFrame({'Aircraft #':['AC-01']*2, 'Execution Doc #':['D1','D2'],
                          'Task #':['139 FIXED S/P AND SCISSORS DI']*2,
                          'd':pd.to_datetime(['2024-01-15','2024-02-02'])})
        return sp, r, t

    def test_document_date_tolerance_is_explicit(self):
        sp, r, t = self.fixture()
        self.assertFalse(construct_intervals(sp, r, t).interval_event.iloc[0])
        out = construct_intervals(sp, r, t, 3)
        self.assertTrue(out.interval_event.iloc[0])
        self.assertEqual(out.lower_date.iloc[0], pd.Timestamp('2024-01-15'))

    def test_wrong_aircraft_or_document_cannot_link(self):
        for field in ('Aircraft #', 'Execution Doc #'):
            sp, r, t = self.fixture()
            t.loc[1, field] = 'wrong'
            self.assertFalse(construct_intervals(sp, r, t, 3).interval_event.iloc[0])

    def test_previous_inspection_must_be_within_installation(self):
        sp, r, t = self.fixture()
        t.loc[0,'d'] = pd.Timestamp('2023-12-31')
        self.assertEqual(construct_intervals(sp, r, t, 3).status.iloc[0],
                         'no_previous_inspection_in_spell')

    def test_ambiguous_source_document_cannot_link(self):
        sp, r, t = self.fixture()
        other = r.copy()
        other['Source Doc #'] = 'D3'
        self.assertFalse(construct_intervals(sp, pd.concat([r,other]), t, 3).interval_event.iloc[0])

    def test_broad_comparison_does_not_require_cycle_data(self):
        dates = pd.date_range('2024-01-01','2024-01-10')
        fh = pd.DataFrame({'AC-01':np.arange(10.)}, index=dates)
        sp = pd.DataFrame({'Part #':['PN']*5, 'Aircraft #':['AC-01']*5,
                           'source':['in_window_removed']*5, 'event':[1]*5,
                           'att':[dates[0]]*5, 'rem':dates[3:8]})
        fits, coverage, _ = compare(sp, fh, pd.DataFrame(), pd.DataFrame(), require_cycles=False)
        self.assertEqual(coverage.retained.iloc[0], 5)
        self.assertEqual(set(fits.scale), {'FH','calendar'})


if __name__ == '__main__':
    unittest.main()
