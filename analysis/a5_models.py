"""Train-only exposure clocks, survival MLE and competing-risk forecasts for A5."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from numpy.polynomial.legendre import leggauss

START=pd.Timestamp('2024-01-01')
END=pd.Timestamp('2026-03-31')
SCALES=('FH','calendar','takeoffs')
NODES,WEIGHTS=leggauss(48)


class Exposure:
    def __init__(self,flights):
        f=flights.copy()
        f['d']=pd.to_datetime(f['Flight Date'],format='%d/%m/%Y')
        self.flights=f
        self.days=pd.date_range(START-pd.Timedelta(days=1),END)
        self.aircraft=sorted(f['Aircraft #'].dropna().unique())
        self._cache={}

    def clocks(self,origin,impute=False):
        key=(origin,bool(impute))
        if key in self._cache:
            return self._cache[key]
        f=self.flights.copy()
        cutoff=origin-pd.Timedelta(days=1)
        train=f[f.d.le(cutoff)]
        paired=train[train.Hours.gt(0)&train['Take Off'].notna()]
        ratios=paired.groupby('Aircraft #')[['Hours','Take Off']].sum()
        ratios=(ratios['Take Off']/ratios.Hours).to_dict()
        counts=f['Take Off'].copy()
        if impute:
            fill=f.Hours*f['Aircraft #'].map(ratios)
            counts=counts.fillna(fill)
        f['cycles']=counts
        f['missing_cycles']=counts.isna().astype(int)
        f['missing_hours']=f.Hours.isna().astype(int)
        f['known_hours']=f.Hours.notna().astype(int)
        daily={}
        for field in ('Hours','cycles','missing_cycles','missing_hours','known_hours'):
            daily[field]=(f.groupby(['d','Aircraft #'])[field].sum().unstack()
                .reindex(index=self.days,columns=self.aircraft).fillna(0.))
        cum={k:v.cumsum() for k,v in daily.items()}
        result=dict(daily=daily,cum=cum,ratios=ratios)
        self._cache[key]=result
        return result

    def values(self,clock,field,aircraft,dates):
        frame=clock['cum'][field]
        return np.array([frame.at[pd.Timestamp(d),ac] for ac,d in zip(aircraft,dates)],float)

    def ages(self,frame,dates,clock,scale):
        if scale=='calendar':
            return (pd.DatetimeIndex(dates)-pd.DatetimeIndex(frame.att)).days.to_numpy(float)
        field='Hours' if scale=='FH' else 'cycles'
        return (self.values(clock,field,frame['Aircraft #'],dates)-
                self.values(clock,field,frame['Aircraft #'],frame.att))

    def incomplete(self,frame,dates,clock,field):
        return (self.values(clock,field,frame['Aircraft #'],dates)-
                self.values(clock,field,frame['Aircraft #'],frame.att))>0

    def rates(self,clock,origin,field):
        cutoff=origin-pd.Timedelta(days=1)
        earlier=cutoff-pd.Timedelta(days=90)
        return (clock['cum'][field].loc[cutoff]-clock['cum'][field].loc[earlier])/90.


def training_view(spells,origin):
    x=spells[spells.att.lt(origin)].copy()
    cutoff=origin-pd.Timedelta(days=1)
    x['observed_removal']=x.rem.lt(origin)&x.source.eq('in_window_removed')
    x['train_event']=x.observed_removal & x.event.eq(1)
    x['competing']=x.observed_removal & x.event.eq(0)
    x['end']=x.rem.where(x.observed_removal,cutoff)
    x['days']=(x.end-x.att).dt.days
    return x


def fit_survival(upper,event,kind,lower=None,interval=None):
    t=np.asarray(upper,float)
    d=np.asarray(event,bool)
    valid=np.isfinite(t)&(t>0)
    excluded=int((~valid & d).sum())
    t,d=t[valid],d[valid]
    result=dict(beta=np.nan,eta=np.nan,converged=False,n=len(t),
                events=int(d.sum()),zero_event_excluded=excluded,intervals=0)
    if d.sum()<5 or t.sum()<=0:
        return result
    scale=float(np.median(t))
    t=t/scale
    lo=t.copy() if lower is None else np.asarray(lower,float)[valid]/scale
    iv=np.zeros(len(t),bool) if interval is None else np.asarray(interval,bool)[valid]
    iv=iv & (lo<t)&(lo>=0)&d
    result['intervals']=int(iv.sum())
    if kind=='exponential' and not iv.any():
        result.update(beta=1.,eta=float(t.sum()*scale/d.sum()),converged=True)
        return result
    def nll(p):
        with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
            b,e=(1.,np.exp(p[0])) if kind=='exponential' else np.exp(p)
            hu=(t/e)**b
            terms=-hu.copy()
            exact=d&~iv
            terms[exact]+=np.log(b)-b*np.log(e)+(b-1)*np.log(t[exact])
            if iv.any():
                hl=(lo[iv]/e)**b
                terms[iv]=-hl+np.log(-np.expm1(-(hu[iv]-hl)))
            value=-terms.sum()
        return float(value) if np.isfinite(value) else 1e100
    starts=([np.log(t.sum()/d.sum())],) if kind=='exponential' else ([0.,0.],[np.log(2.),0.])
    fit=min((minimize(nll,start,method='Nelder-Mead',
                     options={'maxiter':1500,'xatol':1e-7,'fatol':1e-8})
             for start in starts),key=lambda f:f.fun)
    beta,eta=(1.,np.exp(fit.x[0])*scale) if kind=='exponential' else np.exp(fit.x)*[1.,scale]
    ok=fit.success and np.isfinite(fit.fun) and fit.fun<1e99 and np.isfinite([beta,eta]).all()
    result.update(beta=float(beta),eta=float(eta),converged=bool(ok))
    return result


def incidence(age,rate,horizon,beta,eta,nu):
    """CIF under constant exposure rate, quadrature in unscheduled probability."""
    age,rate,horizon,nu=np.broadcast_arrays(np.asarray(age,float),np.asarray(rate,float),
                                          np.asarray(horizon,float),np.asarray(nu,float))
    age=np.maximum(age,0.)
    if beta==1.:
        lam=rate/eta
        total=lam+nu
        return np.divide(lam*(-np.expm1(-total*horizon)),total,
                         out=np.zeros_like(lam),where=total>0)
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        ha=(age/eta)**beta
        delta=((age+rate*horizon)/eta)**beta-ha
        prob=-np.expm1(-np.maximum(delta,0.))
        q=prob[...,None]*(NODES+1)/2
        z=-np.log1p(-q)
        exposure=eta*((ha[...,None]+z)**(1/beta))-age[...,None]
        time=np.divide(exposure,rate[...,None],out=np.zeros_like(exposure),where=rate[...,None]>0)
        time=np.clip(time,0,horizon[...,None])
        cif=prob/2*np.sum(WEIGHTS*np.exp(-nu[...,None]*time),axis=-1)
    return np.clip(np.where(rate>0,cif,0.),0.,1.)


def realized_incidence(age,daily_exposure,beta,eta,nu):
    """Sequential daily exposures preserve horizon order with competing exits."""
    age=np.asarray(age,float).copy()
    survival=np.ones(len(age))
    cumulative=np.zeros(len(age))
    history=[]
    for increments in np.asarray(daily_exposure):
        increment=incidence(age,increments,1.,beta,eta,nu)
        cumulative+=survival*increment
        with np.errstate(over='ignore',invalid='ignore'):
            hazard=((age+increments)/eta)**beta-(age/eta)**beta
        survival*=np.exp(-np.maximum(hazard,0.)-nu)
        age+=increments
        history.append(np.clip(cumulative.copy(),0.,1.))
    return np.array(history)
