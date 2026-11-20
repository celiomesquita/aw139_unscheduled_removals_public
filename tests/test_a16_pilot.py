"""Pilot adapter keeps forecast variants on the same origin-specific training."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
from a16_pilot import PilotEvaluation, synthetic_inputs
from a4_validation import HierarchicalEvaluation


class TestA16Pilot(unittest.TestCase):
    def test_shared_training_is_exactly_reused_and_origins_do_not_leak(self):
        engine = PilotEvaluation.__new__(PilotEvaluation)
        engine._shared_training = {}
        first, second = object(), object()
        origin1, origin2 = pd.Timestamp('2025-01-01'), pd.Timestamp('2025-02-01')
        with patch.object(HierarchicalEvaluation, 'prepare', side_effect=[first, second]) as original:
            self.assertIs(engine.prepare(origin1, 'principal'), first)
            self.assertIs(engine.prepare(origin1, 'realized_fh'), first)
            self.assertIs(engine.prepare(origin2, 'realized_fh'), second)
            self.assertEqual(original.call_count, 2)
            original.assert_any_call(origin1, 'principal')
            original.assert_any_call(origin2, 'principal')
        with self.assertRaises(ValueError):
            engine.prepare(origin1, 'inspection_intervals')

    def test_synthetic_aircraft_copies_are_independent_and_anonymous(self):
        truth = pd.DataFrame({'pn': ['PN'], 'beta': [2.], 'eta': [5.], 'nu': [.01]})
        channels = [dict(pn_index=0, pn='PN', aircraft='AC-01', channel=0,
                         start=0., end=20., curve=np.arange(21, dtype=float), intervals=[(0., 20.)])]
        flights = pd.DataFrame({'Aircraft #': ['AC-01'], 'Hours': [1.], 'Take Off': [1.],
                                'Flight Date': ['02/01/2024']})
        with patch('a16_pilot.pd.read_csv', return_value=flights):
            spells, copied, incomplete = synthetic_inputs(0, truth, channels, copies=2)
        self.assertEqual(set(spells['Aircraft #']), {'AC-01-R01', 'AC-01-R02'})
        self.assertEqual(set(copied['Aircraft #']), {'AC-01-R01', 'AC-01-R02'})
        self.assertTrue(spells.att.le(spells.rem).all())
        self.assertEqual(incomplete, 0)
        self.assertTrue(spells['Serial #'].str.startswith('SIM-').all())
        self.assertTrue(spells.spell_id.is_unique)
        self.assertFalse(spells.loc[spells['Aircraft #'].eq('AC-01-R01'), 'rem'].reset_index(drop=True).equals(
            spells.loc[spells['Aircraft #'].eq('AC-01-R02'), 'rem'].reset_index(drop=True)))


if __name__ == '__main__':
    unittest.main()
