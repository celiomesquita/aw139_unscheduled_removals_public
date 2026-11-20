"""Acceptance checks for T1 and widened operational intervals (T2)."""
import sys
import hashlib
import subprocess
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
PRIVATE_REPOSITORY = (ROOT / 'paper' / 'manuscript.tex').exists() and (ROOT / 'docs').exists()
sys.path.insert(0,str(ROOT/'analysis'))
from round2_survival import bounds,decide_k1
from inspection_censoring import fit_mixed


class TestRound2(unittest.TestCase):
    @unittest.skipUnless(PRIVATE_REPOSITORY, 'public package: requires the private manuscript, docs and Git history')
    def test_scope_closes_manual_review(self):
        scope=(ROOT/'analysis'/'round2_scope.md').read_text(encoding='utf-8')
        for token in ('remoção não programada registrada','297','315','R00173','R00293','R00294','R00328'):
            self.assertIn(token,scope)
        plan=(ROOT/'docs'/'plano_executivo_de_melhorias.md').read_text(encoding='utf-8')
        row=next(s for s in plan.splitlines() if s.startswith('| A3.1 |'))
        self.assertIn('Concluída, resultado inconclusivo',row)
        row=next(s for s in plan.splitlines() if s.startswith('| A3.2 |'))
        self.assertIn('trabalho futuro',row)

    def test_bound_not_before_installation_or_at_removal(self):
        dates=pd.date_range('2024-01-01','2024-01-11')
        sp=pd.DataFrame({'Part #':['PN']*2,'Aircraft #':['AC1']*2,'event':[1,1],
            'att':[dates[2],dates[7]],'rem':[dates[10]]*2,
            'fh_att':[20.,70.],'fh_rem':[100.,100.]})
        tasks=pd.DataFrame({'Aircraft #':['AC1']*2,'Task #':['INSP']*2,'d':[dates[1],dates[5]]})
        mapping=pd.DataFrame({'pn':['PN'],'task':['INSP']})
        clock=pd.DataFrame({'AC1':np.arange(11)*10.},index=dates)
        result=bounds(sp,tasks,mapping,clock,86.)
        self.assertTrue(result.map_interval.all())
        self.assertTrue((result.map_lower_fh>=0).all())
        self.assertTrue((result.map_lower_fh<result.upper_fh).all())
        self.assertEqual(result.map_lower_fh.iloc[0],30.)
        self.assertEqual(result.map_lower_fh.iloc[1],0.)

    def test_known_interval_sample_recovers_beta_eta(self):
        rng=np.random.default_rng(20261112)
        life=400*rng.weibull(2.5,4000)
        event=life<=600
        upper=np.minimum(50*np.ceil(life/50),600)
        lower=np.maximum(0,upper-50)
        fit=fit_mixed(lower,upper,event,event)
        self.assertTrue(fit['converged'])
        self.assertAlmostEqual(fit['beta'],2.5,delta=.15)
        self.assertAlmostEqual(fit['eta'],400,delta=12)

    def test_k1_requires_both_intervals_above_one(self):
        fits=pd.DataFrame({'pn':['A','A','B','B'],'version':['exact','mapped']*2,
            'converged':[True]*4,'beta_lo':[1.2,.9,1.2,1.1]})
        result=decide_k1(fits).set_index('pn')
        self.assertFalse(result.at['A','retained'])
        self.assertTrue(result.at['B','retained'])

    def test_preregistration_contract_without_running_a5(self):
        text=(ROOT/'analysis'/'preregistro_A5.md').read_text(encoding='utf-8')
        for token in ('2025-01','2025-12','20261112','10 000','R00173','R00293',
                      'R00294','R00328','Bernoulli','Brier','Bonferroni','commit',
                      'execução de A5 não iniciada','90 dias','riscos concorrentes'):
            self.assertIn(token,text)

    def test_t2_t4_two_runs_identical(self):
        names=['data/derived/round2_inspection_bounds.csv','data/derived/round2_weibull_fits.csv',
               'data/derived/k1_candidates.csv','analysis/round2_survival_report.md',
               'data/derived/single_removal_cost_documents.csv','data/derived/single_removal_mh_summary.csv',
               'data/derived/visit_gap_summary.csv','config/cost_parameters.csv','analysis/round2_costs_report.md']
        def run():
            for script in ('round2_survival.py','round2_costs.py'):
                subprocess.run([sys.executable,str(ROOT/'analysis'/script)],check=True,capture_output=True)
            return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
        self.assertEqual(run(),run())


if __name__=='__main__':
    unittest.main()
