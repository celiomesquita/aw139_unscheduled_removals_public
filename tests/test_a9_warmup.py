import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a16_generator import sha
from a5_models import training_view
from a9_fitting import PolicyEvaluation, fit_observable, observable_spells
from a9_warmup import (POLICIES, SharedWarmup, RenewalExponential, auxiliary_flights,
                       evaluation_only, generate, training_inputs)


class TestAuthorisedWarmup(unittest.TestCase):
    def inputs(self):
        truth = pd.DataFrame([dict(pn='PN', beta=2., eta=50., nu=.01)])
        channels = [dict(pn_index=0, pn='PN', aircraft='AC-01', channel=0,
                         curve=np.arange(821.), intervals=[(10, 800)])]
        flights = pd.DataFrame({'Aircraft #': ['AC-01'] * 3,
            'Flight Date': ['01/01/2024', '29/02/2024', '31/12/2024'],
            'Hours': [1., 0., 2.], 'Take Off': [1., 0., 1.]})
        return truth, channels, flights

    def test_exact_365_day_shift_does_not_become_calendar_year(self):
        _, _, flights = self.inputs()
        shifted = auxiliary_flights(flights)
        dates = pd.to_datetime(shifted['Flight Date'], format='%d/%m/%Y')
        original = pd.to_datetime(flights['Flight Date'], format='%d/%m/%Y')
        self.assertTrue(((original - dates).dt.days == 365).all())
        self.assertEqual(dates.iloc[1], pd.Timestamp('2023-03-01'))
        self.assertEqual(dates.iloc[-1], pd.Timestamp('2024-01-01'))
        self.assertTrue(shifted['Aircraft #'].str.endswith('-AUX').all())

    def test_late_entries_and_zero_age_preserved_without_continuation(self):
        truth, channels, flights = self.inputs()
        second = dict(channels[0], channel=1, intervals=[(400, 800)])
        spells, shifted, meta = generate(0, 'calibrated', 'verification', truth,
                                         channels + [second], flights)
        self.assertEqual(meta['auxiliary_channels'], 1)
        self.assertEqual(meta['unavailable_first_year_channels'], 1)
        self.assertEqual(spells.att.min(), pd.Timestamp('2024-01-01') + pd.Timedelta(days=10 - 365))
        self.assertTrue((spells.rem <= pd.Timestamp('2024-01-01')).all())
        self.assertFalse(spells.preventive.any())
        self.assertFalse(spells.evaluate.any())
        self.assertTrue(spells['Serial #'].str.startswith('AUX-').all())
        again, clocks, repeated = generate(0, 'calibrated', 'verification', truth,
                                           channels + [second], flights)
        pd.testing.assert_frame_equal(spells, again)
        pd.testing.assert_frame_equal(shifted, clocks)
        self.assertEqual(meta, repeated)

    def test_auxiliary_stream_is_independent_of_phase_risk_and_renewal(self):
        key = [90, 0, 0, 0, 0, 1, 0]
        first, second = RenewalExponential(key, 1), RenewalExponential(key, 1)
        values = [first.exponential() for _ in range(3)]
        self.assertEqual(values, [second.exponential() for _ in range(3)])
        self.assertNotEqual(values[0], RenewalExponential([9, *key[1:]], 1).exponential())
        self.assertNotEqual(values[0], RenewalExponential(key, 2).exponential())
        self.assertNotEqual(values[0], RenewalExponential([90, 1, *key[2:]], 1).exponential())

    def test_finished_auxiliary_censor_never_accumulates_future_time(self):
        truth, channels, flights = self.inputs()
        frame, _, _ = generate(0, 'calibrated', 'verification', truth, channels, flights)
        evaluator = object.__new__(PolicyEvaluation)
        evaluator.spells = frame
        first = training_view(evaluator.cohort(pd.Timestamp('2024-02-01'), 'principal'),
                              pd.Timestamp('2024-02-01'))
        later = training_view(evaluator.cohort(pd.Timestamp('2025-12-01'), 'principal'),
                              pd.Timestamp('2025-12-01'))
        pd.testing.assert_series_equal(first.end, later.end)
        self.assertEqual(set(first.spell_id), set(later.spell_id))
        censored = frame.source.eq('in_window_censored')
        self.assertTrue(first.loc[censored, 'administrative_censor'].all())
        initial = training_view(evaluator.cohort(pd.Timestamp('2024-01-01'), 'principal'),
                                pd.Timestamp('2024-01-01'))
        self.assertTrue(initial.end.lt(pd.Timestamp('2024-01-01')).all())

    def test_all_policies_receive_identical_but_isolated_history(self):
        truth, channels, flights = self.inputs()
        frame, clocks, _ = generate(0, 'calibrated', 'verification', truth, channels, flights)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            frame.to_csv(folder / 'spells.csv', index=False)
            clocks.to_csv(folder / 'flights.csv', index=False)
            (folder / 'manifest.json').write_text(json.dumps(dict(outputs={
                name: sha(folder / name) for name in ('spells.csv', 'flights.csv')})))
            shared = SharedWarmup(folder)
            baseline, _ = shared.for_policy('P0')
            for policy in POLICIES:
                actual, _ = shared.for_policy(policy)
                pd.testing.assert_frame_equal(baseline, actual)
            changed, _ = shared.for_policy('P1')
            changed.loc[:, 'event'] = 999
            untouched, _ = shared.for_policy('P2')
            pd.testing.assert_frame_equal(baseline, untouched)
            empty = observable_spells([], [], pd.Timestamp('2024-01-01'), 730.)
            combined, _ = training_inputs(shared, 'P2', empty, flights)
            self.assertEqual(len(combined), len(frame))
            self.assertTrue(evaluation_only(combined).empty)

    def test_auxiliary_records_never_enter_evaluation_cost(self):
        data = pd.DataFrame({'cohort': ['auxiliary', 'evaluation'], 'cost': [1e9, 2.]})
        self.assertEqual(evaluation_only(data).cost.sum(), 2.)

    def test_channel_without_auxiliary_flights_keeps_calendar_censor(self):
        epoch = pd.Timestamp('2024-01-01')
        spells = observable_spells([dict(unit='AUX-0', pn='PN', aircraft='AC-18-AUX',
            start=-10., end=0., censor_end=0., risk=0, renewal=0)], [], epoch, 0.)
        flights = pd.DataFrame({'Aircraft #': ['AC-01-AUX'],
            'Flight Date': ['01/01/2023'], 'Hours': [1.], 'Take Off': [1.]})
        domain = pd.DataFrame([dict(pn='PN', family='vests', scale='calendar')])
        parameters, metadata = fit_observable(spells, flights, domain, pd.Timestamp('2024-02-01'))
        self.assertEqual(metadata['training_spells'], 1)
        self.assertEqual(parameters['PN']['baseline'], 0.)
        self.assertEqual(parameters['PN']['nu'], 0.)
        self.assertEqual(len(flights), 1)

    def test_administrative_censor_does_not_become_competing_event(self):
        frame = pd.DataFrame(dict(days=[10, 20], pn=['PN', 'PN'],
            competing=[True, True], preventive=[False, False], administrative_censor=[True, False]))
        engine = object.__new__(PolicyEvaluation)
        engine.candidates, engine.fits = ['PN'], []
        with patch('a4_validation.HierarchicalEvaluation.prepare',
                   return_value=(frame, None, None, 0., {'PN': 2 / 30}, {})):
            _, _, _, _, nuisance, _ = engine.prepare(pd.Timestamp('2024-02-01'), 'principal')
        self.assertAlmostEqual(nuisance['PN'], 1 / 30)


if __name__ == '__main__':
    unittest.main()
