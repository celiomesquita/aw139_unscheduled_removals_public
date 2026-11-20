"""A4 estimation adapter for observable, policy-generated renewal spells."""
import numpy as np
import pandas as pd

from a4_validation import HierarchicalEvaluation
from a5_validation import KEYS
from exposure_errata import ObservedExposure
from a9_observations import observable_spells


class PolicyEvaluation(HierarchicalEvaluation):
    def cohort(self, origin, variant):
        frame = super().cohort(origin, variant).copy()
        administrative = frame.source.eq('in_window_censored') & frame.rem.lt(origin)
        frame['administrative_censor'] = administrative
        # A4's historical final censor was always beyond its origins. A9 has
        # completed auxiliary/observation windows whose censor must stay fixed.
        frame.loc[administrative, 'source'] = 'in_window_removed'
        return frame

    def prepare(self, origin, variant):
        train, risk, clock, baseline, nuisance, fits = super().prepare(origin, variant)
        # Preventive interventions censor the lifetime; they are not exogenous exits.
        positive = train.days.gt(0)
        actual_competing = train.competing & ~train.preventive & ~train.administrative_censor
        days = float(train.loc[positive, 'days'].sum())
        global_nu = float(actual_competing[positive].sum() / days) if days else 0.
        for pn in self.candidates:
            mask = positive & train.pn.eq(pn)
            denominator = float(train.loc[mask, 'days'].sum())
            nuisance[pn] = float(actual_competing[mask].sum() / denominator) if denominator else global_nu
        for item in self.fits:
            if item['origin'] == origin and item['variant'] == variant:
                item['competing_rate'] = nuisance[item['pn']]
                item['policy_preventive_excluded_from_nuisance'] = True
                item['administrative_censor_excluded_from_nuisance'] = True
        return train, risk, clock, baseline, nuisance, fits


def fit_observable(spells, flights, domain, origin, minimum_days=30):
    candidates = sorted(domain.pn)
    tasks = pd.DataFrame(columns=['Aircraft #', 'Task #', 'd'])
    mapping = pd.DataFrame(columns=['pn', 'task'])
    removals = pd.DataFrame(columns=['Attached Part #', 'Attached Serial #', 'Aircraft #', 'rem'])
    admin = pd.DataFrame(columns=KEYS)
    evaluator = PolicyEvaluation(spells, flights, candidates, tasks, mapping, removals, admin,
                                 domain=domain)
    evaluator.exposure = ObservedExposure(flights, minimum_days)
    # A channel can exist in the first year without any flight record there.
    # Keep its calendar censor, without inventing a zero-flight observation.
    evaluator.exposure.aircraft = sorted(set(evaluator.exposure.aircraft) |
                                         set(spells['Aircraft #'].dropna()))
    # Only the clock's date support extends. A4 likelihood/bounds/estimator are unchanged.
    first = min(pd.to_datetime(flights['Flight Date'], format='%d/%m/%Y').min(),
                pd.Timestamp(origin) - pd.Timedelta(days=91))
    last = max(pd.to_datetime(flights['Flight Date'], format='%d/%m/%Y').max(), pd.Timestamp(origin))
    evaluator.exposure.days = pd.date_range(first - pd.Timedelta(days=1), last)
    train, _, clock, baseline, nuisance, fits = evaluator.prepare(pd.Timestamp(origin), 'principal')
    if len(train) and train.end.ge(origin).any():
        raise RuntimeError('Future observation entered A9 training')
    output = {}
    for row in domain.itertuples():
        fit = fits.get((row.pn, 'w', row.scale), dict(converged=False))
        output[row.pn] = dict(beta=float(fit['beta']) if fit['converged'] else None,
                              eta=float(fit['eta']) if fit['converged'] else None,
                              converged=bool(fit['converged']), scale=row.scale,
                              nu=float(nuisance[row.pn]), baseline=float(baseline),
                              fallback=None if fit['converged'] else 'A4_constant_baseline')
    return output, dict(effects=evaluator.effects, hyper=evaluator.hyper, reference=evaluator.fits,
                        training_spells=len(train), latest_train_date=str(train.end.max()))
