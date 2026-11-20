"""Marginal Laplace Weibull/exponential random effects; scipy/numpy only."""
import numpy as np
from scipy.optimize import minimize


def likelihood(theta,t,d,pid,n,lower=None,interval=None):
    """NLL, gradient and independent 2x2 observed-information blocks."""
    b=np.exp(theta[pid,0]); x=np.log(t)-theta[pid,1]
    z=b*x
    with np.errstate(over='ignore',invalid='ignore'):
        h=np.exp(np.clip(z,-700,700))
        value=h-d*(theta[pid,0]+z-np.log(t))
        gu=h*z-d*(1+z); gv=b*(d-h)
        huu=h*(z*z+z)-d*z
        huv=b*(d-h*(z+1)); hvv=b*b*h
    if interval is not None and np.any(interval):
        mask=np.asarray(interval,bool)
        l=np.asarray(lower)[mask]
        bm=b[mask]
        zl=np.zeros(len(l)); positive=l>0
        zl[positive]=bm[positive]*(np.log(l[positive])-theta[pid[mask][positive],1])
        hl=np.where(positive,np.exp(np.clip(zl,-700,700)),0.)
        hu=h[mask]; delta=hu-hl
        if np.any(delta<=0):
            return np.inf,np.full((n,2),np.nan),np.full((n,2,2),np.nan)
        q=np.exp(-delta); c=q/(-np.expm1(-delta))
        gl=np.column_stack((hl*zl,-bm*hl))
        gh=np.column_stack((hu*z[mask],-bm*hu))
        Hlo=np.empty((len(l),2,2)); Hhi=np.empty_like(Hlo)
        for H,hh,zz in ((Hlo,hl,zl),(Hhi,hu,z[mask])):
            H[:,0,0]=hh*(zz*zz+zz)
            H[:,0,1]=H[:,1,0]=-bm*hh*(zz+1)
            H[:,1,1]=bm*bm*hh
        diff=gh-gl
        grad=gl-c[:,None]*diff
        Hess=Hlo-c[:,None,None]*(Hhi-Hlo)+(c+c*c)[:,None,None]*diff[:,:,None]*diff[:,None,:]
        value[mask]=hl-np.log(-np.expm1(-delta))
        gu[mask],gv[mask]=grad[:,0],grad[:,1]
        huu[mask],huv[mask],hvv[mask]=Hess[:,0,0],Hess[:,0,1],Hess[:,1,1]
    gradient=np.column_stack([np.bincount(pid,weights=v,minlength=n) for v in (gu,gv)])
    H=np.zeros((n,2,2))
    H[:,0,0]=np.bincount(pid,weights=huu,minlength=n)
    H[:,0,1]=H[:,1,0]=np.bincount(pid,weights=huv,minlength=n)
    H[:,1,1]=np.bincount(pid,weights=hvv,minlength=n)
    return float(value.sum()),gradient,H


def conditional(data,mean,std,bounds,kind='w',details=False):
    n=len(mean)
    active=std>0
    if kind=='e': active[:,0]=False
    base=mean.copy()
    if kind=='e': base[:,0]=0.
    precision=np.divide(1.,std*std,out=np.zeros_like(std),where=active)
    def evaluate(values,detail=False):
        theta=base.copy(); theta[active]=values
        val,grad,H=likelihood(theta,**data)
        delta=theta-base
        val+=.5*np.sum(delta*delta*precision)
        grad+=delta*precision
        if detail:
            H[:,0,0]+=precision[:,0]; H[:,1,1]+=precision[:,1]
            return val,theta,H
        return val,grad[active]
    if active.any():
        result=minimize(evaluate,base[active],jac=True,method='L-BFGS-B',
            bounds=np.array(bounds)[active],options={'maxiter':2000,'ftol':1e-12,'gtol':1e-7,'maxls':40})
        val,theta,H=evaluate(result.x,True)
        ok=result.success and np.isfinite(val)
    else:
        val,theta,H=evaluate(np.array([]),True); ok=np.isfinite(val)
    marginal=val
    for i in range(n):
        dims=np.flatnonzero(active[i])
        if len(dims):
            block=H[i][np.ix_(dims,dims)]
            sign,logdet=np.linalg.slogdet(block)
            if sign<=0 or not np.isfinite(logdet) or np.linalg.eigvalsh(block).min()<=0:
                ok=False; break
            marginal+=np.log(std[i,dims]).sum()+.5*logdet
    if details:return float(marginal),theta,bool(ok),H,active
    return float(marginal),theta,bool(ok)


def laplace_gradient(data,mean,std,bounds,kind='w'):
    value,theta,ok,H,active=conditional(data,mean,std,bounds,kind,True)
    if not ok:return value,np.zeros_like(mean),np.zeros_like(std),False
    _,g,Hlik=likelihood(theta,**data)
    third=[];step=1e-4
    for j in range(2):
        delta=np.zeros_like(theta);delta[:,j]=step
        _,_,plus=likelihood(theta+delta,**data)
        _,_,minus=likelihood(theta-delta,**data)
        third.append((plus-minus)/(2*step))
    gm=np.zeros_like(mean);gs=np.zeros_like(std)
    for i in range(len(mean)):
        dims=np.flatnonzero(active[i])
        if not len(dims):
            gm[i]=g[i];continue
        inverse=np.linalg.inv(H[i][np.ix_(dims,dims)])
        q=np.array([.5*np.trace(inverse@T[i][np.ix_(dims,dims)]) for T in third])
        diff=theta[i]-mean[i]
        for j in range(2):
            tangent=np.zeros(2)
            if active[i,j]:
                k=list(dims).index(j)
                precision=1/std[i,j]**2
                tangent[dims]=inverse[:,k]*precision
                gm[i,j]=-diff[j]*precision+q@tangent
                tangent[dims]=inverse[:,k]*2*diff[j]/std[i,j]**3
                gs[i,j]=(std[i,j]**2-diff[j]**2-inverse[k,k])/std[i,j]**3+q@tangent
            else:
                tangent[j]=1.
                tangent[dims]=-inverse@Hlik[i,dims,j]
                gm[i,j]=g[i,j]+q@tangent
    return value,gm,gs,True


def fit_hierarchy(records,families,kind='w',expanded=False):
    """records: per-P/N t,d,lower,interval arrays, all from one training origin."""
    pns=sorted(records); fams=sorted(set(families[pn] for pn in pns))
    fi=np.array([fams.index(families[pn]) for pn in pns])
    n=len(pns); nf=len(fams)
    t=np.concatenate([records[p]['t'] for p in pns])
    d=np.concatenate([records[p]['d'] for p in pns]).astype(bool)
    low=np.concatenate([records[p]['lower'] for p in pns])
    iv=np.concatenate([records[p]['interval'] for p in pns]).astype(bool)
    pid=np.concatenate([np.full(len(records[p]['t']),i) for i,p in enumerate(pns)])
    data=dict(t=t,d=d,pid=pid,n=n,lower=low,interval=iv)
    etab=[]; mueta=[]
    factor=1000 if expanded else 100
    for fam in fams:
        indices=[i for i,p in enumerate(pns) if families[p]==fam]
        values=t[np.isin(pid,indices)]
        events=d[np.isin(pid,indices)].sum()
        etab.append((np.log(values.min()/factor),np.log(values.max()*factor)))
        mueta.append(np.log(values.sum()/max(1,events)))
    ub=(np.log(.05),np.log(40 if expanded else 20))
    bounds=np.array([[ub,etab[fi[i]]] for i in range(n)])
    # Hypervector: mean log beta, family means log eta, global sd beta, family sd eta.
    hb=[ub,*etab,(0.,4. if expanded else 2.),*[(0.,6. if expanded else 3.)]*nf]
    if kind=='e': hb[0]=(0.,0.); hb[1+nf]=(0.,0.)
    for j in range(nf):
        if sum(fi[i]==j and len(records[p]['t'])>0 for i,p in enumerate(pns))==1:
            hb[2+nf+j]=(0.,0.)
    calls=[0]
    def decode(h):
        mean=np.column_stack((np.full(n,h[0]),np.array(h[1:1+nf])[fi]))
        std=np.column_stack((np.full(n,h[1+nf]),np.array(h[2+nf:])[fi]))
        return mean,std
    def objective(h,detail=False,derivative=False):
        calls[0]+=1
        mean,std=decode(h)
        if derivative:
            val,gm,gs,ok=laplace_gradient(data,mean,std,bounds,kind)
            grad=np.array([gm[:,0].sum(),*[gm[fi==j,1].sum() for j in range(nf)],
                gs[:,0].sum(),*[gs[fi==j,1].sum() for j in range(nf)]])
            return (val,grad) if ok and np.isfinite(val) else (1e100,np.zeros(len(h)))
        val,theta,ok=conditional(data,mean,std,bounds,kind)
        if detail:return val,theta,ok
        return val if ok and np.isfinite(val) else 1e100
    attempts=[]
    for beta in ((1.,2.) if kind=='w' else (1.,)):
        for sd in (.25,1.):
            initial=np.array([np.log(beta),*mueta,sd,*([sd]*nf)])
            initial=np.array([np.clip(v,*bound) for v,bound in zip(initial,hb)])
            result=minimize(lambda h:objective(h,derivative=True),initial,jac=True,method='L-BFGS-B',bounds=hb,
                options={'maxiter':2000,'ftol':1e-8,'eps':1e-4,'maxls':30})
            attempts.append(result)
    # Explicit all-zero face is the grouped likelihood, optimised without effects.
    zero_bounds=hb.copy()
    for k in range(1+nf,len(hb)):zero_bounds[k]=(0.,0.)
    initial=np.array([0.,*mueta,*([0.]*(nf+1))])
    pooled=minimize(lambda h:objective(h,derivative=True),initial,jac=True,method='L-BFGS-B',bounds=zero_bounds,
        options={'maxiter':2000,'ftol':1e-8,'maxls':30})
    attempts.append(pooled)
    eligible=[r for r in attempts if r.success and r.fun<1e99]
    if not eligible:
        return {},dict(converged=False,attempts=len(attempts),successful_attempts=0,evaluations=calls[0])
    best=min(eligible,key=lambda r:r.fun)
    # Evaluate each zero-variance face explicitly at the fitted hypermeans.
    choices=[best.x.copy()]
    for j in range(1+nf,len(hb)):
        face=best.x.copy(); face[j]=0.; choices.append(face)
    hyper=min(choices,key=objective)
    if not np.array_equal(hyper,best.x):
        face_bounds=hb.copy()
        for j in range(1+nf,len(hb)):
            if hyper[j]==0:face_bounds[j]=(0.,0.)
        refined=minimize(lambda h:objective(h,derivative=True),hyper,jac=True,method='L-BFGS-B',bounds=face_bounds,
            options={'maxiter':2000,'ftol':1e-8,'eps':1e-4,'maxls':30})
        hyper=refined.x if refined.success and refined.fun<=best.fun else best.x
    val,theta,ok=objective(hyper,True)
    boundary=any(np.isclose(theta[i,k],bounds[i,k,0],atol=1e-5) or
                 np.isclose(theta[i,k],bounds[i,k,1],atol=1e-5) for i in range(n) for k in range(2))
    boundary=boundary or any(np.isclose(hyper[j],hb[j][1],atol=1e-5) for j in range(1+nf,len(hb)) if hb[j][1]>0)
    result={p:dict(beta=float(np.exp(theta[i,0])),eta=float(np.exp(theta[i,1])),
        converged=ok,n=len(records[p]['t']),events=int(records[p]['d'].sum()),
        zero_event_excluded=records[p].get('zero_event_excluded',0),intervals=int(records[p]['interval'].sum()))
        for i,p in enumerate(pns)}
    meta=dict(converged=ok,attempts=len(attempts),successful_attempts=len(eligible),evaluations=calls[0],objective=val,
        mu_beta=float(hyper[0]),tau_beta=float(hyper[1+nf]),boundary=bool(boundary),
        zero_variance=bool(np.any(hyper[1+nf:]==0)))
    for j,fam in enumerate(fams):
        meta['mu_eta_'+fam]=float(hyper[1+j]); meta['tau_eta_'+fam]=float(hyper[2+nf+j])
    return result,meta
