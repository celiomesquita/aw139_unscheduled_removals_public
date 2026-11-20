import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_environment import Environment
from a9_observations import observable_spells
from a9_simulation import simulate_policy
from a9_static import calibrate_threshold
from a9_warmup import POLICIES
from a9_parallel import CalibrationExecutor


class ArtificialHistory:
    def for_policy(self, policy):
        frame = observable_spells([dict(unit='AUX-0', pn='PN', aircraft='AC-01-AUX',
            start=-10., end=0., censor_end=0., risk=0, renewal=0)], [], pd.Timestamp('2024-01-01'), 0.)
        frame['spell_id'] = ['AUX-000']
        frame['cohort'], frame['evaluate'] = 'auxiliary', False
        flights = pd.DataFrame({'Aircraft #': ['AC-01-AUX'], 'Flight Date': ['01/01/2023'],
                                'Hours': [1.], 'Take Off': [1.]})
        return frame, flights


class TestSixPolicyIntegration(unittest.TestCase):
    def inputs(self, units=1, aging=False):
        dates = pd.date_range('2024-01-01', periods=61)
        flights = pd.DataFrame({'Aircraft #': 'AC-01', 'Flight Date': dates.strftime('%d/%m/%Y'),
                                'Hours': 1., 'Take Off': 1.})
        stops = pd.DataFrame({'Aircraft #': 'AC-01', 'start': ['2024-01-11', '2024-02-10', '2024-03-01']})
        beta, eta = (2., 20.) if aging else (1., 3.)
        truth = pd.DataFrame([dict(pn='PN', beta=beta, eta=eta, nu=.05)])
        channels = [dict(pn_index=0, pn='PN', aircraft='AC-01', channel=i, start=0, end=60,
                         curve=np.arange(61.), intervals=[(0, 60)]) for i in range(units)]
        domain = pd.DataFrame([dict(pn='PN', scale='calendar', family='rotor')])
        models = {'PN': dict(beta=beta, eta=eta, nu=.05, baseline=.3, converged=True, scale='calendar',
                             log_eta_lo=float(np.log(eta) - .1), log_eta_hi=float(np.log(eta) + .1))}
        cell = dict(index=0, level='calibrated', knowledge='realized_fh', r=5., scenario='A')
        return truth, channels, domain, models, cell, Environment(flights, stops)

    def execute(self, policy, units=1, aging=False, calibration_executor=None):
        truth, channels, domain, models, cell, environment = self.inputs(units, aging)
        def fixed_fit(spells, flights, domain, origin, threshold):
            self.assertTrue(spells.cohort.eq('auxiliary').any())
            return copy.deepcopy(models), dict(training_spells=len(spells))
        context = [dict(daily=[1.], visits=[0.], weight=units)] if aging else []
        threshold = calibrate_threshold(context, models['PN']['beta'], models['PN']['eta'],
                                         .05, 5.)[0] if aging else np.inf
        return simulate_policy(policy, cell, 0, 'verification', ArtificialHistory(), models,
            {'PN': threshold}, {'PN': context}, {'AC-01': 1.}, truth, channels, domain, environment,
            {'PN': 1.}, origins=list(pd.date_range('2024-01-01', '2024-02-01', freq='MS')),
            end_day=60, refit=fixed_fit, calibration_executor=calibration_executor)

    def test_six_complete_stationary_null_paths_share_random_numbers(self):
        first = [self.execute(p) for p in POLICIES]
        second = [self.execute(p) for p in POLICIES]
        for a, b in zip(first, second):
            self.assertEqual(a['cost'], b['cost'])
            self.assertEqual(a['events'], b['events'])
            self.assertEqual(a['detection'], b['detection'])
            self.assertEqual(a['preventive'], 0)
            self.assertTrue(all(e['cohort'] == 'evaluation' and not e['unit'].startswith('AUX')
                                for e in a['events']))
        self.assertTrue(all(p['cost'] == first[0]['cost'] for p in first))
        self.assertTrue(all(p['unscheduled'] == first[0]['unscheduled'] for p in first))

    def test_six_complete_aging_paths_include_preventive_actions_and_are_deterministic(self):
        first = [self.execute(p, units=4, aging=True) for p in POLICIES]
        second = [self.execute(p, units=4, aging=True) for p in POLICIES]
        self.assertGreater(sum(p['preventive'] for p in first), 0)
        for a, b in zip(first, second):
            self.assertEqual(a['events'], b['events'])
            self.assertEqual(a['cost'], b['cost'])
            self.assertEqual(a['detection'], b['detection'])

    def test_spawned_calibration_preserves_all_six_policy_paths(self):
        serial = [self.execute(p, units=4, aging=True) for p in POLICIES]
        with CalibrationExecutor(2) as executor:
            parallel = [self.execute(p, units=4, aging=True, calibration_executor=executor) for p in POLICIES]
        for first, second in zip(serial, parallel):
            self.assertEqual(first['events'], second['events'])
            self.assertEqual(first['cost'], second['cost'])
            self.assertEqual(first['detection'], second['detection'])

    def test_executed_plan_is_checked_against_capacity(self):
        with patch('a9_simulation.planned_actions', return_value=(
                {('AC-01', 40): {'EVAL-0-1-0', 'EVAL-0-1-1'}}, [])):
            with self.assertRaisesRegex(RuntimeError, 'capacity'):
                self.execute('P2', units=4)

    def test_manual_feasible_preventive_restarts_one_unit_only(self):
        with patch('a9_simulation.planned_actions', return_value=(
                {('AC-01', 40): {'EVAL-0-1-0'}}, [])):
            result = self.execute('P2', units=4)
        self.assertEqual(result['preventive'], 1)
        self.assertEqual([e['unit'] for e in result['events'] if e['risk'] == 3], ['EVAL-0-1-0'])


if __name__ == '__main__':
    unittest.main()
