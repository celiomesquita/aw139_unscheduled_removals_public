"""Section 4 surrogate. No age minimisation before nine references are frozen."""
import json
import math
from pathlib import Path
import warnings

import numpy as np
from scipy.integrate import IntegrationWarning, quad
from scipy.optimize import minimize_scalar
from scipy.special import gamma, gammaincc

EPSABS, EPSREL = 1e-10, 1e-8


def visit_summary(context):
    daily = np.asarray(context['daily'], float)
    if daily.ndim != 1 or not len(daily) or not np.isfinite(daily).all() or (daily < 0).any():
        raise ValueError('INVALID_HISTORICAL_CLOCK')
    visits = np.array(sorted(set(context['visits'])), float)
    if not np.isfinite(visits).all() or (visits < 0).any() or (visits >= len(daily)).any():
        raise ValueError('INVALID_HISTORICAL_VISITS')
    gaps = np.diff(np.r_[visits, visits[0]+len(daily)]) if len(visits) else np.array([])
    return dict(u=float(daily.sum()/len(daily)), period=len(daily), visits=len(visits),
                excess=float((gaps*gaps).sum()/(2*gaps.sum())) if len(gaps) else None,
                weight=float(context.get('weight', 1.)))


def _survival(t, u, beta, eta, nu):
    hazard = (u*t/eta)**beta + nu*t
    return math.exp(-hazard) if hazard < 746 else 0.


def tail_endpoint(u, beta, eta, nu):
    if not (u>0 and beta>0 and eta>0 and nu>=0):
        raise ValueError('INVALID_SURVIVAL_MODEL')
    end = min(eta/u, 1/nu if nu else math.inf)
    for _ in range(128):
        survival = _survival(end,u,beta,eta,nu)
        bound = (survival/nu if nu else eta/u*gamma(1/beta)/beta*
                 gammaincc(1/beta,(u*end/eta)**beta))
        if survival <= 1e-10 and bound <= 1e-7:
            return end, survival, float(bound)
        end *= 2
    raise ArithmeticError('SURROGATE_TAIL_NOT_BOUNDED')


def context_rate(age, context, beta, eta, nu, r):
    summary = visit_summary(context)
    u = summary['u']
    if not summary['visits'] or u == 0:
        # Threshold-independent groups are omitted consistently with emenda 011.
        return summary['weight']*summary['visits']/summary['period'] if age==0 and summary['visits'] else 0.
    if not (age>=0 and beta>0 and eta>0 and nu>=0 and r>0):
        raise ValueError('INVALID_AGE_MODEL')
    infinite = math.isinf(age)
    end = tail_endpoint(u,beta,eta,nu)[0] if infinite else age/u+summary['excess']
    power = max(1, math.ceil(4/beta))
    upper = end**(1/power)
    def duration(x):
        t=x**power
        return _survival(t,u,beta,eta,nu)*power*x**(power-1)
    def unscheduled(x):
        t=x**power
        return _survival(t,u,beta,eta,nu)*beta*power*(u/eta)**beta*x**(power*beta-1)
    with warnings.catch_warnings():
        warnings.simplefilter('error',IntegrationWarning)
        d, de = quad(duration,0,upper,epsabs=EPSABS,epsrel=EPSREL,limit=200)
        failure, fe = quad(unscheduled,0,upper,epsabs=EPSABS,epsrel=EPSREL,limit=200)
    if d<=0 or not all(math.isfinite(x) for x in (d,de,failure,fe)):
        raise ArithmeticError('INVALID_RENEWAL_INTEGRAL')
    preventive = 0. if infinite else _survival(end,u,beta,eta,nu)
    return summary['weight']*(r*failure+nu*d+preventive)/d


def expected_rate(age, contexts, beta, eta, nu, r):
    return math.fsum(context_rate(age,c,beta,eta,nu,r) for c in contexts)


def require_manifest(path):
    from amendment015.state import digest
    path=Path(path)
    if not path.is_file():
        raise RuntimeError('NINE_EXACT_REFERENCES_NOT_FROZEN')
    value=json.loads(path.read_text())
    if (value.get('status')!='complete' or value.get('N')!=9 or
        len(value.get('references',[]))!=9 or
        {r['id'] for r in value['references']}!={f'{i:02d}' for i in range(9)}):
        raise RuntimeError('NINE_EXACT_REFERENCES_NOT_FROZEN')
    config_path=path.parent.parent/'configuration.json'
    if digest(config_path)!=value['configuration_sha256']:
        raise RuntimeError('CONFIGURATION_CHANGED_AFTER_FREEZE')
    if value['age_source_sha256'] != digest(__file__):
        raise RuntimeError('AGE_SOURCE_CHANGED_AFTER_FREEZE')
    for record in value['references']:
        if digest(path.parent/record['certificate'])!=record['sha256']:
            raise RuntimeError('EXACT_CERTIFICATE_HASH_MISMATCH')
    return value


def calibrate(contexts, beta, eta, nu, r, *, manifest_path):
    require_manifest(manifest_path)  # Even synthetic minimisation must wait.
    if beta<=1:
        return math.inf, dict(reason='nonincreasing_hazard_no_preventive')
    if not any(visit_summary(c)['visits'] and visit_summary(c)['u']>0 for c in contexts):
        return math.inf, dict(reason='no_informative_initial_visit_calendar')
    grid=np.linspace(math.log(1e-6), math.log(1e3),129)
    function=lambda x:expected_rate(eta*math.exp(x),contexts,beta,eta,nu,r)
    values=[function(x) for x in grid]
    candidates=[(values[i],eta*math.exp(x)) for i,x in enumerate(grid)]
    candidates += [(expected_rate(0.,contexts,beta,eta,nu,r),0.),
                   (expected_rate(math.inf,contexts,beta,eta,nu,r),math.inf)]
    for i in range(1,len(grid)-1):
        if values[i]<=values[i-1] and values[i]<=values[i+1]:
            result=minimize_scalar(function,bounds=(grid[i-1],grid[i+1]),method='bounded',options={'xatol':1e-8})
            if not result.success:
                raise ArithmeticError('AGE_MINIMISATION_FAILED')
            candidates.append((float(result.fun),eta*math.exp(float(result.x))))
    minimum=min(x[0] for x in candidates)
    tied=[x for x in candidates if x[0]<=minimum+1e-12]
    cost,age=max(tied,key=lambda x:x[1])
    if age>0 and math.isfinite(age) and any(abs(math.log(age/eta)-x)<=1e-8 for x in (grid[0],grid[-1])):
        raise ArithmeticError('FINITE_MINIMUM_AT_DOMAIN_EDGE')
    return age,dict(reason='weighted_classical_age_rate',rate=cost,candidate_points=len(candidates))
