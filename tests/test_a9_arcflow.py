import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_arcflow import RenewalArc, solve_paths
from a9_milp import SequenceColumn, solve_sequences


class TestArcFlow(unittest.TestCase):
    def test_compact_paths_equal_all_sequences(self):
        arcs = []
        for u in ('A', 'B'):
            for a in range(-1, 3):
                for b in range(a + 1, 4):
                    cost = (b - a) ** 2 + (1 if b < 3 else 0)
                    if u == 'B':
                        cost += (b + 1) / 10
                    arcs.append(RenewalArc(u, a, b, cost))
        table = {(a.unit, a.start, a.end): a.cost for a in arcs}
        columns = []
        for u in ('A', 'B'):
            for mask in itertools.product((False, True), repeat=3):
                p = tuple(i for i, present in enumerate(mask) if present)
                cost = sum(table[u, a, b] for a, b in zip((-1,) + p, p + (3,)))
                columns.append(SequenceColumn(u, p, cost))
        mh, capacity = {'A': 2., 'B': 3.}, [3., 3., 3.]
        selected, explicit = solve_sequences(columns, mh, capacity)
        paths, compact = solve_paths(arcs, mh, capacity)
        self.assertTrue(compact['proven_optimal'])
        self.assertAlmostEqual(explicit['selected_expected_cost'], compact['selected_expected_cost'])
        expected = {c.unit: c.visits for c in selected}
        self.assertEqual(paths, expected)


if __name__ == '__main__':
    unittest.main()
