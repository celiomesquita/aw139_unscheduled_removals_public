"""Tests for analysis/feasibility.py. Run: py -3 -m unittest discover -s tests"""
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import feasibility as f  # noqa: E402


def weibull_sample(beta, eta, n, seed, censor_at=None, entry_max=0.0):
    """Weibull lives, optional fixed right censoring and left truncation (delayed entry)."""
    rng = np.random.default_rng(seed)
    e = rng.uniform(0, entry_max, 4 * n) if entry_max else np.zeros(4 * n)
    life = eta * rng.weibull(beta, 4 * n)
    keep = life > e                      # truncation: units failing before entry are never seen
    e, life = e[keep][:n], life[keep][:n]
    if censor_at is None:
        return life, np.ones(n), e
    t = np.minimum(life, censor_at)
    return t, (life <= censor_at).astype(int), e


class TestWeibullMLE(unittest.TestCase):
    def test_complete_sample(self):
        b, eta, lo, hi, ok = f.weibull_fit(*weibull_sample(2.0, 500.0, 3000, 1))
        self.assertTrue(ok)
        self.assertAlmostEqual(b, 2.0, delta=0.1)
        self.assertAlmostEqual(eta, 500.0, delta=20.0)
        self.assertLess(lo, 2.0)
        self.assertGreater(hi, 2.0)

    def test_right_censoring(self):
        t, d, e = weibull_sample(3.0, 330.0, 3000, 2, censor_at=350.0)
        self.assertGreater((d == 0).mean(), 0.2)
        b, eta, *_ = f.weibull_fit(t, d, e)
        self.assertAlmostEqual(b, 3.0, delta=0.15)
        self.assertAlmostEqual(eta, 330.0, delta=12.0)

    def test_left_truncation(self):
        t, d, e = weibull_sample(1.5, 1000.0, 3000, 3, censor_at=2000.0, entry_max=800.0)
        b, eta, *_ = f.weibull_fit(t, d, e)
        self.assertAlmostEqual(b, 1.5, delta=0.1)
        self.assertAlmostEqual(eta, 1000.0, delta=60.0)

    def test_exponential_ci_covers_one(self):
        b, _, lo, hi, _ = f.weibull_fit(*weibull_sample(1.0, 800.0, 400, 4, censor_at=1500.0))
        self.assertLess(lo, 1.0)
        self.assertGreater(hi, 1.0)


class TestRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f.report.clear()
        cls.omth = f.load_omth()
        cls.clock, cls.rate, cls.anchor = f.build_clock(cls.omth)
        cls.r = f.load_removals()
        cls.sp = f.build_spells(cls.r, cls.clock, cls.rate)

    def test_omth_dates_month_first_inside_window(self):
        d = self.omth.d.dropna()
        self.assertGreaterEqual(d.min(), f.START)
        self.assertLessEqual(d.max(), f.END)
        self.assertTrue((d == d.dt.normalize()).all())

    def test_removals_clean(self):
        self.assertFalse(self.r["Part #"].isna().any())
        self.assertFalse(self.r.drop(columns=["att", "rem", "event", "tracked"]).duplicated().any())
        self.assertTrue(self.r.loc[self.r.tracked, "att"].notna().all())

    def test_clock_complete_monotone_and_anchored(self):
        self.assertFalse(self.clock.isna().any().any())
        self.assertTrue((self.clock.diff().iloc[1:] >= 0).all().all())
        self.assertLess(self.anchor.mad.max(), 10.0)

    def test_spells_consistent(self):
        sp = self.sp
        self.assertFalse(sp["Aircraft #"].isna().any())
        self.assertTrue((sp.t_fh > 0).all())
        self.assertTrue((sp.entry_fh <= sp.t_fh + 1e-9).all())
        self.assertTrue((sp.loc[sp.att >= f.START, "entry_fh"] == 0).all())
        self.assertTrue((sp.loc[sp.source == "in_window_censored", "event"] == 0).all())
        self.assertTrue((sp.rem <= f.END).all())


class TestReproducibility(unittest.TestCase):
    def test_two_runs_identical(self):
        def run():
            subprocess.run([sys.executable, str(ROOT / "analysis" / "feasibility.py")],
                           check=True, capture_output=True)
            files = sorted((ROOT / "data" / "derived").glob("*.csv")) + [f.REPORT]
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
