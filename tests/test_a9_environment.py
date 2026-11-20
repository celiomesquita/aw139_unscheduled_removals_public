from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_environment import END_DAY, Environment


class TestOperationalInformation(unittest.TestCase):
    def environment(self, scenario='A'):
        flights = pd.DataFrame({'Aircraft #': ['AC-01'] * 3,
            'Flight Date': ['01/01/2024', '15/11/2025', '01/12/2025'],
            'Hours': [2., 0., 4.], 'Take Off': [1., 0., 2.]})
        stops = pd.DataFrame({'Aircraft #': ['AC-01'], 'start': ['2024-01-10']})
        return Environment(flights, stops, scenario)

    def test_future_flights_do_not_enter_the_past_rate(self):
        env = self.environment()
        self.assertEqual(env.observed_rate('AC-01', pd.Timestamp('2025-12-01')), 0.)
        projected, _ = env.forecast('AC-01', pd.Timestamp('2025-12-01'), 3, 'principal', 'FH')
        self.assertEqual(projected.tolist(), [0., 0., 0.])

    def test_imposed_utilisation_changes_only_after_full_initial_year(self):
        env = self.environment('B-util')
        self.assertEqual(env.increment('AC-01', 0), 2.)
        self.assertAlmostEqual(env.increment('AC-01', END_DAY - 30), 5.2)
        self.assertAlmostEqual(env.increment('AC-01', END_DAY + 1), 2.6)

    def test_partial_history_is_unavailable_without_zero_imputation(self):
        flights = pd.DataFrame({'Aircraft #': ['AC-22'], 'Flight Date': ['15/11/2025'],
                                'Hours': [0.], 'Take Off': [0.]})
        env = Environment(flights, pd.DataFrame(columns=['Aircraft #', 'start']))
        self.assertIsNone(env.observed_rate('AC-22', pd.Timestamp('2025-12-01')))


if __name__ == '__main__':
    unittest.main()
