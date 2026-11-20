"""T14 tests use synthetic inputs only; no corrected real-data execution."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
from a5_models import Exposure, END, SCALES
from a5_validation import Evaluation
from a4_validation import HierarchicalEvaluation
from exposure_errata import ObservedExposure, CorrectedA5, CorrectedA4


def flights(start, end='2026-03-31', hours=2.):
    days = pd.date_range(start, end)
    return pd.DataFrame({'Aircraft #': ['AC-01'] * len(days),
        'Flight Date': days.strftime('%d/%m/%Y'), 'Hours': hours, 'Take Off': 1.})


def engine(kind, data, att):
    instance = kind.__new__(kind)
    corrected = kind in (CorrectedA5, CorrectedA4)
    instance.exposure = ObservedExposure(data) if corrected else Exposure(data)
    instance.candidates = ['PN']
    instance.domain = pd.DataFrame({'pn': ['PN'], 'family': ['rotor'], 'scale': ['FH']}).set_index('pn')
    risk = pd.DataFrame({'spell_id': ['SIM-1'], 'pn': ['PN'], 'Aircraft #': ['AC-01'],
        'att': [pd.Timestamp(att)], 'rem': [END], 'event': [0], 'source': ['in_window_censored']})
    def prepare(origin, variant):
        fitted = {(pn, prefix, scale): dict(beta=2. if prefix == 'w' else 1., eta=400., converged=True)
                  for pn in ['PN'] for prefix in ('w', 'e') for scale in SCALES}
        return (pd.DataFrame(), risk, instance.exposure.clocks(origin), .002, {'PN': .001}, fitted)
    instance.prepare = prepare
    return instance


class TestExposureErrata(unittest.TestCase):
    def test_late_entry_counts_calendar_days_and_threshold_30(self):
        data = flights('2025-11-15')
        data.loc[0, ['Hours', 'Take Off']] = np.nan  # Any record establishes entry.
        source = ObservedExposure(data)
        origin = pd.Timestamp('2025-12-01')
        self.assertEqual(source.observed_days(origin)['AC-01'], 16)
        self.assertTrue(np.isnan(source.rates(source.clocks(origin), origin, 'Hours')['AC-01']))
        origin = pd.Timestamp('2025-12-15')
        self.assertEqual(source.observed_days(origin)['AC-01'], 30)
        self.assertAlmostEqual(source.rates(source.clocks(origin), origin, 'Hours')['AC-01'], 58 / 30)

    def test_only_prespecified_sensitivity_60(self):
        data = flights('2025-11-01')
        source = ObservedExposure(data, 60)
        origin = pd.Timestamp('2025-12-15')
        self.assertTrue(np.isnan(source.rates(source.clocks(origin), origin, 'cycles')['AC-01']))
        origin = pd.Timestamp('2025-12-31')
        self.assertEqual(source.observed_days(origin)['AC-01'], 60)
        self.assertEqual(source.rates(source.clocks(origin), origin, 'cycles')['AC-01'], 1.)
        with self.assertRaises(ValueError):
            ObservedExposure(data, 45)

    def test_exit_does_not_invent_an_observation_end_or_new_rate(self):
        source = ObservedExposure(flights('2025-11-01', '2025-11-15'))
        origin = pd.Timestamp('2026-02-01')
        self.assertEqual(source.observed_days(origin)['AC-01'], 90)
        clock = source.clocks(origin)
        self.assertEqual(source.rates(clock, origin, 'Hours')['AC-01'],
                         source.legacy.rates(clock, origin, 'Hours')['AC-01'])

    def test_recorded_zero_flights_remain_zero_available_exposure(self):
        data = flights('2024-10-01', hours=0.)
        source = ObservedExposure(data)
        origin = pd.Timestamp('2025-01-01')
        self.assertEqual(source.rates(source.clocks(origin), origin, 'Hours')['AC-01'], 0.)
        frame = engine(CorrectedA5, data, '2024-11-01').forecast(origin, 'principal')
        self.assertTrue(frame.w_FH.eq(0).all())
        self.assertFalse(frame.w_FH_fallback.any())

    def test_A4_unavailable_exposure_has_identical_hW_hE_baseline_fallback(self):
        instance = engine(CorrectedA4, flights('2025-11-15'), '2025-11-16')
        frame = instance.forecast(pd.Timestamp('2025-12-01'), 'principal')
        for name in ('w_FH', 'e_FH', 'w_takeoffs', 'e_takeoffs'):
            np.testing.assert_array_equal(frame[name], frame.baseline)
            self.assertTrue(frame[name + '_fallback'].all())
            self.assertTrue(frame[name + '_reason'].eq('baseline_observed_days_lt_30').all())
        selected = instance.select(frame, [], 'principal', pd.Timestamp('2025-12-01'))
        np.testing.assert_array_equal(selected.w_selected, selected.e_selected)

    def test_A5_unavailable_exposure_uses_own_calendar_model_with_marker(self):
        frame = engine(CorrectedA5, flights('2025-11-15'), '2025-11-16').forecast(
            pd.Timestamp('2025-12-01'), 'principal')
        for prefix in ('w', 'e'):
            np.testing.assert_array_equal(frame[prefix + '_FH'], frame[prefix + '_calendar'])
            self.assertTrue(frame[prefix + '_FH_fallback'].all())
            self.assertTrue(frame[prefix + '_FH_reason'].eq('calendar_observed_days_lt_30').all())

    def test_complete_windows_reproduce_all_original_prediction_columns_exactly(self):
        data = flights('2024-10-01')
        origin = pd.Timestamp('2025-01-01')
        for original, corrected in ((Evaluation, CorrectedA5), (HierarchicalEvaluation, CorrectedA4)):
            before = engine(original, data, '2024-11-01').forecast(origin, 'principal')
            after = engine(corrected, data, '2024-11-01').forecast(origin, 'principal')
            pd.testing.assert_frame_equal(before, after[before.columns], check_exact=True)

    def test_realized_variant_is_entirely_original_even_with_incomplete_window(self):
        data = flights('2025-11-15')
        origin = pd.Timestamp('2025-12-01')
        for original, corrected in ((Evaluation, CorrectedA5), (HierarchicalEvaluation, CorrectedA4)):
            before = engine(original, data, '2025-11-16').forecast(origin, 'realized_fh')
            instance = engine(corrected, data, '2025-11-16')
            after = instance.forecast(origin, 'realized_fh')
            pd.testing.assert_frame_equal(before, after, check_exact=True)
            self.assertIsInstance(instance.exposure, ObservedExposure)


if __name__ == '__main__':
    unittest.main()
