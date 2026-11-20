"""Frozen prediction reanalysis must reproduce A4 and leave its files untouched."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_REPOSITORY = (ROOT / 'paper' / 'manuscript.tex').exists() and (ROOT / 'docs').exists()
sys.path.insert(0, str(ROOT / 'analysis'))
from a15_stability import protected_hashes
from machine_reproduction import OLD_HOST_ATOL, OLD_HOST_RTOL


class TestA15(unittest.TestCase):
    @unittest.skipUnless(PRIVATE_REPOSITORY, 'public package: requires the private manuscript, docs and Git history')
    def test_frozen_reanalysis_is_deterministic_and_preserves_a4_a5(self):
        before = protected_hashes()
        subprocess.run([sys.executable, str(ROOT / 'analysis/a15_stability.py')],
                       cwd=ROOT, check=True)
        out = ROOT / 'data/derived/a15'
        first = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
        subprocess.run([sys.executable, str(ROOT / 'analysis/a15_stability.py')],
                       cwd=ROOT, check=True)
        self.assertEqual(first, {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()})
        self.assertEqual(before, protected_hashes())
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertTrue(manifest['full_year_reproduced'])
        self.assertEqual(manifest['absolute_tolerance'], OLD_HOST_ATOL)
        self.assertEqual(manifest['relative_tolerance'], OLD_HOST_RTOL)
        self.assertEqual(manifest['same_host_comparison'], 'bitwise')
        self.assertEqual(manifest['fits_executed'], 0)
        check = pd.read_csv(out / 'bootstrap_check.csv')
        self.assertTrue(check.same_decision.all())
        self.assertTrue(check.same_PN.all())
        intervals = pd.read_csv(out / 'intervals.csv')
        self.assertEqual(len(intervals), 2 * 3 * 2 * 12)
        self.assertNotIn('outcome', intervals.columns)
        self.assertEqual(set(intervals.period), {'2025', 'jan-jun', 'jul-dez'})


if __name__ == '__main__':
    unittest.main()
