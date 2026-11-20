"""Prespecified A5 checks, before execution of real-data validation."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import quad

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'analysis'))
from a5_models import Exposure,training_view,fit_survival,incidence,realized_incidence
from a5_validation import Evaluation,log_score,cluster_means,bootstrap_decision


class TestA5(unittest.TestCase):
    def test_future_event_cannot_change_training_view(self):
        sp=pd.DataFrame({'att':pd.to_datetime(['2024-01-01','2024-02-01','2025-02-01']),
             'rem':pd.to_datetime(['2024-03-01','2025-03-01','2025-04-01']),
             'event':[1,1,1],'source':['in_window_removed']*3})
        origin=pd.Timestamp('2025-01-01')
        first=training_view(sp,origin)
        changed=sp.copy()
        changed.loc[1,'rem']=pd.Timestamp('2026-01-01')
        changed.loc[1,'event']=0
        changed.loc[2,'event']=0
        second=training_view(changed,origin)
        pd.testing.assert_frame_equal(first[['att','end','train_event','competing','days']],
                                      second[['att','end','train_event','competing','days']])

    def test_probability_and_monotonicity(self):
        for beta in (.6,1.,3.):
            p=incidence(200.,3.,np.array([30.,60.,90.]),beta,500.,.002)
            self.assertTrue(((p>=0)&(p<=1)).all())
            self.assertTrue((np.diff(p)>=0).all())

    def test_competing_incidence_matches_direct_integral(self):
        age,rate,h,beta,eta,nu=200.,3.,90.,2.5,500.,.005
        expected=quad(lambda t:np.exp(-(((age+rate*t)/eta)**beta-(age/eta)**beta)-nu*t)*
                      beta/eta*((age+rate*t)/eta)**(beta-1)*rate,0,h)[0]
        self.assertAlmostEqual(float(incidence(age,rate,h,beta,eta,nu)),expected,places=7)
        without=incidence(age,rate,h,beta,eta,0.)
        self.assertLess(incidence(age,rate,h,beta,eta,nu),without)

    def test_realized_path_preserves_zero_usage_and_horizon_order(self):
        p=realized_incidence([0.,100.],np.array([[0.,2.],[3.,0.],[0.,4.]]),2.,500.,.003)
        self.assertEqual(p[0,0],0.)
        self.assertTrue((np.diff(p,axis=0)>=0).all())

    def test_future_flights_cannot_change_past_imputation(self):
        f=pd.DataFrame({'Aircraft #':['AC1']*3,'Flight Date':['01/01/2024','02/01/2024','02/01/2025'],
                        'Hours':[2.,3.,100.],'Take Off':[4.,np.nan,900.]})
        origin=pd.Timestamp('2025-01-01')
        one=Exposure(f).clocks(origin,True)
        f.loc[2,['Hours','Take Off']]=[999.,9999.]
        two=Exposure(f).clocks(origin,True)
        pd.testing.assert_frame_equal(one['cum']['cycles'].loc[:'2024-12-31'],
                                      two['cum']['cycles'].loc[:'2024-12-31'])

    def simulated_comparison(self,beta):
        rng=np.random.Generator(np.random.PCG64(20261112))
        life=400*rng.weibull(beta,6000)
        t=np.minimum(life,600.)
        fitw=fit_survival(t,life<=600,'weibull')
        fite=fit_survival(t,life<=600,'exponential')
        age=rng.uniform(0,500,6000)
        residual=400*((age/400)**beta+rng.exponential(size=6000))**(1/beta)-age
        y=residual<=90
        pw=incidence(age,1.,90.,fitw['beta'],fitw['eta'],0.)
        pe=incidence(age,1.,90.,1.,fite['eta'],0.)
        delta=log_score(y,pw)-log_score(y,pe)
        means=np.array([delta[np.arange(len(delta))%24==i].mean() for i in range(24)])
        draws=rng.integers(0,24,size=(10000,24))
        return np.quantile(means[draws].mean(axis=1),[.025,.975])

    def test_beta_one_no_systematic_gain_over_exponential(self):
        lo,hi=self.simulated_comparison(1.)
        self.assertLessEqual(lo,0.)
        self.assertGreaterEqual(hi,0.)

    def test_beta_three_improves_on_exponential(self):
        lo,_=self.simulated_comparison(3.)
        self.assertGreater(lo,0.)

    def test_missing_takeoffs_does_not_drop_other_model_predictions(self):
        dates=pd.date_range('2024-01-01','2025-03-31',freq='D')
        f=pd.DataFrame({'Aircraft #':['AC1']*len(dates),'Flight Date':dates.strftime('%d/%m/%Y'),
                        'Hours':np.ones(len(dates)),'Take Off':np.full(len(dates),np.nan)})
        sp=pd.DataFrame({'Part #':['PN']*7,'Serial #':['S'+str(i) for i in range(7)],
             'Aircraft #':['AC1']*7,'att':pd.to_datetime(['2024-01-01']*7),
             'rem':pd.to_datetime(['2024-03-01','2024-04-01','2024-05-01','2024-06-01',
                                   '2024-07-01','2024-08-01','2025-03-15']),
             'event':[1]*7,'source':['in_window_removed']*7})
        removals=pd.DataFrame(columns=['Attached Part #','Attached Serial #','Aircraft #','rem'])
        tasks=pd.DataFrame(columns=['Aircraft #','Task #','d'])
        mapping=pd.DataFrame(columns=['pn','task'])
        admin=sp.iloc[:0]
        engine=Evaluation(sp,f,['PN'],tasks,mapping,removals,admin)
        predictions=engine.forecast(pd.Timestamp('2025-01-01'),'principal')
        self.assertEqual(len(predictions),3)
        self.assertTrue(predictions.w_takeoffs_fallback.all())
        self.assertTrue(np.isfinite(predictions[['w_FH','w_calendar','baseline']]).all().all())
        self.assertTrue(predictions.spell_id.nunique()==1)

    def test_internal_scale_selection_excludes_future_targets(self):
        engine=Evaluation.__new__(Evaluation)
        engine.candidates=['PN']
        engine.selections=[]
        past=pd.DataFrame({'pn':['PN','PN'],'y':[1,1],
            'target_end':pd.to_datetime(['2024-12-01','2025-02-01'])})
        frame=pd.DataFrame({'pn':['PN']})
        for prefix in ('w','e'):
            for scale,values in [('FH',[.1,.999]),('calendar',[.9,.001]),('takeoffs',[.2,.99])]:
                name=f'{prefix}_{scale}'
                past[name]=values
                past[name+'_fallback']=False
                frame[name]=.3
                frame[name+'_fallback']=False
        result=engine.select(frame,[past],'principal',pd.Timestamp('2025-01-01'))
        self.assertEqual(result.w_selected_scale.iloc[0],'calendar')
        self.assertTrue(all(r['latest_internal_end']<pd.Timestamp('2025-01-01') for r in engine.selections))

    def test_competing_exit_before_origin_is_not_a_risk_unit(self):
        sp=pd.DataFrame({'att':pd.to_datetime(['2024-01-01']),
             'rem':pd.to_datetime(['2024-11-01']),'event':[0],'source':['in_window_removed']})
        train=training_view(sp,pd.Timestamp('2025-01-01'))
        self.assertTrue(train.competing.iloc[0])
        self.assertFalse((sp.att.lt('2025-01-01')&sp.rem.ge('2025-01-01')).any())


if __name__=='__main__':
    unittest.main()
