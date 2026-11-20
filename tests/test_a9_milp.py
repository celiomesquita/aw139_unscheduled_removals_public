import itertools
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
import mip
from a9_milp import SequenceColumn, feasible_plan, solve_sequences


class TestA9MILP(unittest.TestCase):
    def instance(self):
        columns = [SequenceColumn('A', (), 12.), SequenceColumn('A', (0,), 4.),
                   SequenceColumn('A', (1,), 5.), SequenceColumn('A', (0, 2), 1.),
                   SequenceColumn('B', (), 11.), SequenceColumn('B', (0,), 2.),
                   SequenceColumn('B', (1,), 6.), SequenceColumn('B', (2,), 3.),
                   SequenceColumn('B', (0, 2), 0.)]
        return columns, {'A': 2., 'B': 3.}, [3., 3., 3.]

    def test_two_units_three_visits_matches_complete_enumeration(self):
        columns, mh, cap = self.instance()
        feasible = [p for p in itertools.product([c for c in columns if c.unit == 'A'],
                                                [c for c in columns if c.unit == 'B'])
                    if feasible_plan(p, mh, cap)]
        optimum = min(sum(c.expected_cost for c in p) for p in feasible)
        self.assertEqual(optimum, 5.)
        first, diagnostic = solve_sequences(columns, mh, cap)
        second, repeat = solve_sequences(columns, mh, cap)
        self.assertTrue(diagnostic['proven_optimal'])
        self.assertEqual(diagnostic['selected_expected_cost'], optimum)
        self.assertEqual(first, second)
        self.assertEqual({(c.unit, c.visits) for c in first}, {('A', (1,)), ('B', (0, 2))})
        self.assertTrue(feasible_plan(first, mh, cap))

    def test_timeout_preserves_feasible_previous_actions_or_none(self):
        columns, mh, cap = self.instance()
        with patch.object(mip.Model, 'optimize', return_value=mip.OptimizationStatus.NO_SOLUTION_FOUND):
            chosen, info = solve_sequences(columns, mh, cap, [columns[1], columns[5]])
            self.assertEqual(info['fallback'], 'no_preventive')
            self.assertTrue(all(not c.visits for c in chosen))
            chosen, info = solve_sequences(columns, mh, cap, [columns[2], columns[8]])
            self.assertEqual(info['fallback'], 'previous_feasible')
            self.assertFalse(info['proven_optimal'])
            self.assertTrue(feasible_plan(chosen, mh, cap))

    def test_zero_capacity_and_absent_mh(self):
        columns, mh, cap = self.instance()
        chosen, info = solve_sequences(columns, mh, [0., 0., 0.])
        self.assertTrue(all(not c.visits for c in chosen))
        mh['B'] = 0.
        with self.assertRaisesRegex(ValueError, 'positive preventive MH'):
            solve_sequences(columns, mh, cap)


if __name__ == '__main__':
    unittest.main()
