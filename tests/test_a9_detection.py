from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_detection import DriftDetector, log_eta_intervals


class TestObservableDetection(unittest.TestCase):
    def test_zero_random_effect_variance_does_not_give_zero_uncertainty(self):
        records = {'PN': dict(t=np.array([.5, 1., 2., 3.]), d=np.ones(4))}
        effect = {'PN': dict(beta=1., eta=1.625)}
        hyper = dict(tau_beta=0., tau_eta_rotor=0.)
        first = log_eta_intervals(records, effect, {'PN': 'rotor'}, hyper)['PN']
        self.assertGreater(first['log_eta_se'], 0.)
        doubled = {'PN': {k: np.tile(v, 2) for k, v in records['PN'].items()}}
        second = log_eta_intervals(doubled, effect, {'PN': 'rotor'}, hyper)['PN']
        self.assertAlmostEqual(first['log_eta_se'] / second['log_eta_se'], np.sqrt(2), places=10)

    def test_parameter_and_exposure_alarms_use_observations_only(self):
        detector = DriftDetector({'PN': dict(log_eta_lo=2.)}, ['PN'], {'AC-01': 10.})
        detector.observe(1, {'PN': dict(log_eta_hi=2.1)}, {'AC-01': 12.})
        self.assertFalse(detector.parameter_first)
        self.assertFalse(detector.exposure_first)
        detector.observe(2, {'PN': dict(log_eta_hi=1.9)}, {'AC-01': 12.})
        self.assertEqual(detector.parameter_first['PN'], 2)
        self.assertEqual(detector.exposure_first['AC-01'], 2)

    def test_unassessable_is_not_a_negative_alarm(self):
        detector = DriftDetector({'PN': dict(log_eta_lo=None)}, ['PN'], {'AC-01': None})
        detector.observe(1, {'PN': dict(log_eta_hi=1.)}, {'AC-01': 100.})
        self.assertTrue(all(not r['assessable'] for r in detector.rows))


if __name__ == '__main__':
    unittest.main()
