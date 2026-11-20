"""A4_v1 synthetic acceptance tests before real-data fitting."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'analysis'))
from a4_models import likelihood,conditional,fit_hierarchy,laplace_gradient
from a5_models import fit_survival
from a5_models import training_view
import pandas as pd
from a5_validation import preserve_initial_manifest,bootstrap_decision,log_score


def sample(groups):
    rng=np.random.default_rng(20261112)
    b=np.exp(np.log(2)+rng.normal(0,.25,11))
    e=np.exp(np.log(400)+rng.normal(0,.35,11))
    records={};families={}
    for i in range(11):
        life=e[i]*rng.weibull(b[i],1000)
        t=np.minimum(life,800)
        records[str(i)]=dict(t=t,d=life<=800,lower=t.copy(),interval=np.zeros(len(t),bool))
        families[str(i)]=groups[i]
    return records,families,b,e


class TestA4(unittest.TestCase):
    def test_unit_aggregation_is_not_equal_aircraft_weighting(self):
        frame=pd.DataFrame({'aircraft':['A']*10+['B'],'origin':['2025-01-01']*11,
            'horizon':[1]*11,'pn':['PN']*11,'y':[1]*11,'w_selected':[.9]*10+[.1],'baseline':[.5]*11})
        _,one,_=bootstrap_decision(frame,['A','B'],['PN'],aggregation='unit')
        _,two,_=bootstrap_decision(frame,['A','B'],['PN'])
        delta=log_score(frame.y,frame.w_selected)-log_score(frame.y,frame.baseline)
        self.assertAlmostEqual(one.loc[one.pn=='aggregate','delta_log'].iloc[0],delta.mean())
        self.assertNotAlmostEqual(one.delta_log.iloc[0],two.delta_log.iloc[0])

    def test_laplace_hyper_gradient_matches_finite_difference(self):
        rng=np.random.default_rng(20261112)
        t=np.concatenate([350*rng.weibull(2.,60),500*rng.weibull(2.5,60)])
        data=dict(t=t,d=np.ones(len(t),bool),pid=np.repeat([0,1],60),n=2)
        bounds=np.array([[(np.log(.05),np.log(20)),(np.log(.1),np.log(1e6))]]*2)
        mean=np.log([[2.,400.],[2.,400.]])
        std=np.array([[.3,.4],[.3,.4]])
        _,gm,gs,ok=laplace_gradient(data,mean,std,bounds)
        self.assertTrue(ok)
        for matrix,gradient in ((mean,gm),(std,gs)):
            for j in range(2):
                step=np.zeros_like(matrix);step[:,j]=1e-4
                if matrix is mean:
                    a=conditional(data,mean+step,std,bounds)[0]
                    b=conditional(data,mean-step,std,bounds)[0]
                else:
                    a=conditional(data,mean,std+step,bounds)[0]
                    b=conditional(data,mean,std-step,bounds)[0]
                self.assertAlmostEqual(gradient[:,j].sum(),(a-b)/2e-4,delta=.02)

    def test_analytic_gradient_and_hessian(self):
        t=np.array([10.,20.,30.,40.]);d=np.array([1,1,0,1],bool)
        args=dict(t=t,d=d,pid=np.zeros(4,int),n=1,lower=np.array([5.,20.,30.,30.]),
                  interval=np.array([1,0,0,1],bool))
        theta=np.log([[2.,35.]])
        value,g,H=likelihood(theta,**args)
        h=1e-5
        for j in range(2):
            delta=np.zeros((1,2));delta[0,j]=h
            a,ga,_=likelihood(theta+delta,**args)
            b,gb,_=likelihood(theta-delta,**args)
            self.assertAlmostEqual(g[0,j],(a-b)/(2*h),places=5)
            np.testing.assert_allclose(H[0,:,j],(ga-gb)[0]/(2*h),rtol=1e-5,atol=1e-5)

    def test_variance_zero_and_infinite_conditional_limits(self):
        rng=np.random.default_rng(20261112)
        t=400*rng.weibull(2,1000);d=np.ones(len(t),bool)
        data=dict(t=t,d=d,pid=np.zeros(len(t),int),n=1)
        mean=np.log([[1.5,350.]])
        bounds=np.array([[(np.log(.05),np.log(20)),(np.log(.1),np.log(1e6))]])
        _,zero,ok=conditional(data,mean,np.zeros((1,2)),bounds)
        self.assertTrue(ok);np.testing.assert_array_equal(zero,mean)
        _,flat,ok=conditional(data,mean,np.full((1,2),1e8),bounds)
        self.assertTrue(ok)
        independent=fit_survival(t,d,'weibull')
        np.testing.assert_allclose(np.exp(flat[0]),[independent['beta'],independent['eta']],rtol=1e-4)

    def test_sparse_shape_shrinks_with_known_eta(self):
        rng=np.random.default_rng(20261112)
        t=400*rng.weibull(3,8);d=np.ones(8,bool)
        data=dict(t=t,d=d,pid=np.zeros(8,int),n=1)
        bounds=np.array([[(np.log(.05),np.log(20)),(np.log(.1),np.log(1e6))]])
        mean=np.log([[2.,400.]])
        _,individual,_=conditional(data,mean,np.array([[1e8,0.]]),bounds)
        _,shrunk,ok=conditional(data,mean,np.array([[.2,0.]]),bounds)
        self.assertTrue(ok)
        self.assertTrue(min(individual[0,0],mean[0,0])<=shrunk[0,0]<=max(individual[0,0],mean[0,0]))

    def test_recover_eleven_pn_one_and_three_families(self):
        for groups in (['all']*11,['rotor']*7+['wheels']*2+['vests']*2):
            records,families,b,e=sample(groups)
            fitted,h=fit_hierarchy(records,families)
            self.assertTrue(h['converged'])
            self.assertAlmostEqual(h['mu_beta'],np.log(b).mean(),delta=.20)
            self.assertAlmostEqual(h['tau_beta'],np.log(b).std(),delta=.25)
            for fam in set(groups):
                mask=np.array(groups)==fam
                self.assertAlmostEqual(h['mu_eta_'+fam],np.log(e[mask]).mean(),delta=.25)
                self.assertAlmostEqual(h['tau_eta_'+fam],np.log(e[mask]).std(),delta=.25)

    def test_a5_manifest_preserves_original_execution_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            archive=path/'original.json';dest=path/'manifest.json'
            archive.write_text('{"execution_git_revision":"aed4c3a"}\n',encoding='utf-8')
            dest.write_text('{"execution_git_revision":"new"}\n',encoding='utf-8')
            preserve_initial_manifest(dest,archive,dict(execution_git_revision='new'))
            self.assertEqual(dest.read_bytes(),archive.read_bytes())

    def test_future_event_and_deterministic_hyperparameters(self):
        rows=[]
        for pn in ('A','B'):
            for days in (20,40,60,80,100,450):
                rows.append(dict(pn=pn,att=pd.Timestamp('2024-01-01'),
                    rem=pd.Timestamp('2024-01-01')+pd.Timedelta(days=days),
                    source='in_window_removed',event=1))
        frame=pd.DataFrame(rows);origin=pd.Timestamp('2025-01-01')
        def records(x):
            v=training_view(x,origin)
            return {pn:dict(t=g.days.to_numpy(float),d=g.train_event.to_numpy(),
                lower=g.days.to_numpy(float),interval=np.zeros(len(g),bool)) for pn,g in v.groupby('pn')}
        first=records(frame)
        frame.loc[frame.rem.ge(origin),'rem']=pd.Timestamp('2026-01-01')
        frame.loc[frame.rem.ge(origin),'event']=0
        second=records(frame)
        for pn in first:
            for field in first[pn]:np.testing.assert_array_equal(first[pn][field],second[pn][field])
        one,h1=fit_hierarchy(first,{'A':'rotor','B':'rotor'})
        two,h2=fit_hierarchy(second,{'A':'rotor','B':'rotor'})
        self.assertTrue(h1['converged'])
        self.assertEqual(h1,h2)
        self.assertEqual(one,two)


if __name__=='__main__':unittest.main()
