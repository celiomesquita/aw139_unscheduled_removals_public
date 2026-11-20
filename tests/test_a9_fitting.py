from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_fitting import observable_spells
from a5_models import training_view


class TestPolicyObservations(unittest.TestCase):
    def test_latent_fractional_ages_are_not_exposed_to_estimation(self):
        epoch = pd.Timestamp('2024-01-01')
        item = dict(unit='SIM-0', pn='PN', aircraft='AC-01', start=.2, end=3.6,
                    renewal=0, risk=3, age=123.456)
        frame = observable_spells([item], [], epoch, 10.)
        self.assertNotIn('age', frame)
        self.assertEqual(frame.att.iloc[0], epoch + pd.Timedelta(days=1))
        self.assertEqual(frame.rem.iloc[0], epoch + pd.Timedelta(days=4))
        train = training_view(frame, epoch + pd.Timedelta(days=6))
        self.assertFalse(train.train_event.iloc[0])
        self.assertTrue(train.preventive.iloc[0])
        self.assertEqual(train.days.iloc[0], 3)

    def test_future_event_is_censored_at_training_cut(self):
        epoch = pd.Timestamp('2024-01-01')
        item = dict(unit='SIM-1', pn='PN', aircraft='AC-01', start=0., end=20.,
                    renewal=0, risk=1)
        frame = observable_spells([item], [], epoch, 30.)
        train = training_view(frame, epoch + pd.Timedelta(days=10))
        self.assertFalse(train.train_event.iloc[0])
        self.assertEqual(train.end.iloc[0], epoch + pd.Timedelta(days=9))


if __name__ == '__main__':
    unittest.main()
