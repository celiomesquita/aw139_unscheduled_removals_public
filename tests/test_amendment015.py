"""A015 kernels and clocks only: no cheap optimum before the real manifest."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import json

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
from amendment015.age import visit_summary,context_rate,expected_rate,tail_endpoint,calibrate
from amendment015.state import START,END
from amendment015 import state
from amendment015.references import diagnostic_json
from amendment015.execution import AgeCalibrationExecutor, run_replica


class TestAmendment015(unittest.TestCase):
    def test_fixed_global_clock_is_336_hours(self):
        self.assertEqual(START,datetime(2026,11,18,15,57,28,tzinfo=timezone.utc))
        self.assertEqual(END-START,timedelta(hours=336))

    def test_empirical_excess_uses_all_cyclic_intervals(self):
        context=dict(daily=[2.]*10,visits=[1,3,7,7],weight=1)
        result=visit_summary(context)
        self.assertEqual(result['u'],2.)
        self.assertEqual(result['excess'],(4+16+16)/20)

    def test_exponential_cost_rate_without_prevention(self):
        context=dict(daily=[1.]*10,visits=[1,5],weight=2.)
        # Unscheduled rate .1, competing rate .05, costs 5 and 1.
        self.assertAlmostEqual(context_rate(math.inf,context,1.,10.,.05,5.),2*(.1*5+.05),places=8)

    def test_weibull_run_to_failure_mean(self):
        context=dict(daily=[1.]*10,visits=[1,5],weight=1.)
        self.assertAlmostEqual(context_rate(math.inf,context,2.,10.,0.,5.),5/(10*math.gamma(1.5)),places=8)

    def test_sum_of_weighted_rates_not_ratio_of_sums(self):
        contexts=[dict(daily=[1.]*10,visits=[1,5],weight=w) for w in [2.,3.]]
        one=context_rate(5.,dict(daily=[1.]*10,visits=[1,5],weight=1.),2.,10.,.05,5.)
        self.assertAlmostEqual(expected_rate(5.,contexts,2.,10.,.05,5.),5*one,places=12)

    def test_zero_clock_positive_age_is_constant_and_zero_age_has_visits(self):
        context=dict(daily=[0.]*10,visits=[1,5],weight=3.)
        self.assertEqual(context_rate(2.,context,2.,10.,.05,5.),0.)
        self.assertEqual(context_rate(0.,context,2.,10.,.05,5.),.6)

    def test_tail_controls(self):
        _,probability,duration=tail_endpoint(1.,2.,10.,.05)
        self.assertLessEqual(probability,1e-10)
        self.assertLessEqual(duration,1e-7)

    def test_finite_exponential_rate_includes_delay_and_preventive_cost(self):
        context=dict(daily=[2.]*10,visits=[0,5],weight=3.)
        end=4./2.+2.5
        duration=-math.expm1(-.25*end)/.25
        expected=3.*(.2*5.+.05+math.exp(-.25*end)/duration)
        self.assertAlmostEqual(context_rate(4.,context,1.,10.,.05,5.),expected,places=10)

    def test_resume_preserves_reference_deadline_and_never_adds_stage_durations(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            start=START+timedelta(hours=1)
            (out/'time_ledger.json').write_text(json.dumps(dict(commit=state.COMMIT,
                start_utc=START.isoformat(),stage_events=[],reference_preparation_start_utc=None)))
            with patch.object(state,'OUT',out),patch.object(state,'utcnow',return_value=start):
                first=state.ledger('preparation',begin_references=True)
            later=start+timedelta(hours=2)
            with patch.object(state,'OUT',out),patch.object(state,'utcnow',return_value=later):
                second=state.ledger('calculation',begin_references=True)
                state.check_deadline(references=True)
            self.assertEqual(first['reference_deadline_utc'],second['reference_deadline_utc'])
            self.assertEqual(second['consumed_seconds'],3*3600)
            self.assertEqual(second['reference_consumed_seconds'],2*3600)
            self.assertEqual(second['stage_events'][0]['wall_seconds'],2*3600)
            with patch.object(state,'OUT',out),patch.object(state,'utcnow',return_value=start+timedelta(hours=24)):
                with self.assertRaisesRegex(TimeoutError,'GLOBAL_24H'):
                    state.check_deadline(references=True)

    def test_only_missing_diagnostics_become_json_null(self):
        import pandas as pd
        source=dict(beta=np.float64(2.),missing=float('nan'),origin=pd.Timestamp('2026-01-01'))
        self.assertEqual(diagnostic_json(source),dict(beta=2.,missing=None,origin='2026-01-01T00:00:00'))

    def test_no_age_even_infinite_fallback_before_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            for beta in [1.,2.]:
                with self.assertRaisesRegex(RuntimeError,'NINE_EXACT_REFERENCES'):
                    calibrate([],beta,10.,.05,5.,manifest_path=Path(folder)/'absent.json')

    def test_policy_integration_cannot_start_before_nine_references(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest=Path(folder)/'absent.json'
            with self.assertRaisesRegex(RuntimeError,'NINE_EXACT_REFERENCES'):
                with AgeCalibrationExecutor(manifest=manifest):
                    self.fail('executor entered without real references')
            with self.assertRaisesRegex(RuntimeError,'NINE_EXACT_REFERENCES'):
                run_replica(None,None,None,None,None,None,None,None,None,None,manifest=manifest)

    def test_worker_count_leaves_room_for_coordinator_and_tracker(self):
        for workers in [0,7,8]:
            with self.assertRaises(ValueError):
                AgeCalibrationExecutor(workers)
