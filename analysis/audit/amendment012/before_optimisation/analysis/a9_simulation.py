"""Six policy paths with common exogenous clocks and renewal-indexed random numbers."""
import copy
import math
import time

import numpy as np
import pandas as pd

from a16_generator import START
from a9_detection import DriftDetector
from a9_environment import CHANGE_DAY, END_DAY, Environment, historical_calendars
from a9_evaluation import initial_units
from a9_events import eta_factor
from a9_fitting import fit_observable
from a9_observations import observable_spells
from a9_planning import optimise_visit_plan
from a9_renewal import RenewalCosts
from a9_static import calibrate_threshold
from a9_warmup import POLICIES, evaluation_only, training_inputs


def calibrate_all(models, contexts, r, heartbeat=None):
    thresholds, diagnostics = {}, {}
    for pn in sorted(models):
        if heartbeat:
            heartbeat(stage='P1_calibration', pn=pn)
        model = models[pn]
        if not model['converged'] or not contexts.get(pn):
            thresholds[pn] = math.inf
            diagnostics[pn] = dict(reason='initial_model_or_calendar_unavailable')
        else:
            thresholds[pn], diagnostics[pn] = calibrate_threshold(
                contexts[pn], model['beta'], model['eta'], model['nu'], r)
    return thresholds, diagnostics


def policy_observations(entries, cutoff):
    records = []
    for entry in entries:
        if entry['start'] > cutoff:
            continue
        latent = list(entry['completed'])
        state = entry['state']
        if state.birth < entry['end']:
            latent.append(dict(start=state.birth, end=entry['end'], censor_end=entry['end'],
                               risk=0, renewal=state.renewal))
        for observation, (left, right) in enumerate(entry['intervals']):
            if left > cutoff:
                continue
            for event in latent:
                if event['end'] <= left or event['start'] >= right or event['start'] < left:
                    continue
                risk = event['risk'] if event['end'] <= right else 0
                end = min(event['end'], right)
                records.append(dict(unit=entry['unit'] + '-' + str(observation),
                    pn=entry['pn'], aircraft=entry['aircraft'], start=event['start'],
                    end=end, censor_end=end, risk=risk, renewal=event['renewal']))
    frame = observable_spells(records, [], START, END_DAY)
    frame['cohort'], frame['evaluate'] = 'evaluation', True
    return frame


def forecast_spec(entry, model, environment, origin, horizon, knowledge, r):
    cutoff = (origin - START).days - 1
    length = horizon - cutoff
    age = environment.age(entry, cutoff)
    daily, reason = environment.forecast(entry['aircraft'], origin,
                                         length + environment.period, knowledge, model['scale'])
    if not model['converged'] or age is None or daily is None:
        unknown_age = age is None
        daily = np.full(length + environment.period, model['baseline'])
        beta, eta, age = 1., 1., 0.
        reason = reason or ('unobserved_current_installation' if unknown_age else 'unavailable_fit')
    else:
        beta, eta = model['beta'], model['eta']
    return dict(unit=entry['unit'], age=age, daily=daily[:length], beta=beta, eta=eta,
                nu=model['nu'], r=r, terminal_daily=daily[length:], mh=entry['mh'],
                fallback=reason, full_forecast=daily)


def planned_actions(entries, models, environment, origin, knowledge, r, previous=None):
    cutoff = (origin - START).days - 1
    final = (origin + pd.DateOffset(months=6) - START).days - 1
    schedule, diagnostics = {}, []
    for aircraft in environment.aircraft:
        active = [e for e in entries if e['aircraft'] == aircraft and e['start'] <= cutoff < e['end']]
        if not active:
            continue
        visits = environment.visits(aircraft, cutoff, final)
        if not visits:
            continue
        capacities = [sum(e['mh'] for e in entries if e['aircraft'] == aircraft and
                          e['start'] <= v <= e['end']) / 4 for v in visits]
        specifications = []
        for entry in active:
            end = min(final, entry['end'])
            spec = forecast_spec(entry, models[entry['pn']], environment, origin, end, knowledge, r)
            local = [(j, v) for j, v in enumerate(visits) if v <= end]
            spec['visits'] = [v - cutoff for _, v in local]
            spec['visit_indices'] = [j for j, _ in local]
            specifications.append(spec)
        old = None
        if previous:
            old = {e['unit']: tuple(j for j, v in enumerate(visits)
                                   if e['unit'] in previous.get((aircraft, v), ())) for e in active}
        paths, info = optimise_visit_plan(specifications, capacities, old)
        for unit, indices in paths.items():
            for j in indices:
                schedule.setdefault((aircraft, visits[j]), set()).add(unit)
        diagnostics.append(dict(aircraft=aircraft, origin=str(origin.date()), **info))
    return schedule, diagnostics


def projected_visit_age(entry, model, environment, origin, knowledge, day):
    cutoff = (origin - START).days - 1
    if not model['converged']:
        return None, None
    full, _ = environment.forecast(entry['aircraft'], origin, day - cutoff, knowledge, model['scale'])
    if full is None:
        return None, None
    birth = int(np.ceil(entry['state'].birth))
    known = any(a <= entry['state'].birth and day <= b for a, b in entry['intervals'])
    if not known:
        return None, None
    if birth <= cutoff:
        age = float(max(0, cutoff - birth)) if model['scale'] == 'calendar' else float(
            environment.cumulative.at[environment.date(cutoff), entry['aircraft']] -
            environment.cumulative.at[environment.date(birth), entry['aircraft']])
        first = 0
    else:
        age, first = 0., birth - cutoff
    return age + float(full[first:].sum()), full


def avoided_per_mh(entry, model, environment, origin, knowledge, day, age, r):
    cutoff = (origin - START).days - 1
    final = (origin + pd.DateOffset(months=6) - START).days - 1
    full, _ = environment.forecast(entry['aircraft'], origin, final - cutoff + environment.period,
                                    knowledge, model['scale'])
    offset = day - cutoff
    daily = full[offset:final - cutoff]
    times = np.arange(len(daily) + 1.)
    clock = np.r_[0., np.cumsum(daily)]
    costs = RenewalCosts(times, clock, model['beta'], model['eta'], model['nu'], r, order=32)
    terminal = full[final - cutoff:]
    old, _ = costs.current(age, len(daily), terminal)
    new, _ = costs.current(0., len(daily), terminal)
    return (old - new - 1) / entry['mh']


def age_actions(entries, models, thresholds, environment, origin, knowledge, day, r):
    selected = set()
    for aircraft in environment.aircraft:
        if day not in environment.stops[aircraft]:
            continue
        active = [e for e in entries if e['aircraft'] == aircraft and e['start'] <= day <= e['end']]
        capacity = sum(e['mh'] for e in active) / 4
        eligible = []
        for entry in active:
            threshold = thresholds.get(entry['pn'], math.inf)
            if not math.isfinite(threshold):
                continue
            age, _ = projected_visit_age(entry, models[entry['pn']], environment, origin, knowledge, day)
            if age is not None and age >= threshold:
                eligible.append((entry, age))
        if sum(e['mh'] for e, _ in eligible) > capacity + 1e-9:
            scored = [(avoided_per_mh(e, models[e['pn']], environment, origin, knowledge, day, a, r), e)
                      for e, a in eligible]
            ordered = [e for _, e in sorted(scored, key=lambda item: (
                -item[0], item[1]['pn'], item[1]['channel'], item[1]['unit']))]
        else:
            ordered = [e for e, _ in eligible]
        for entry in ordered:
            if entry['mh'] <= capacity + 1e-9:
                selected.add(entry['unit'])
                capacity -= entry['mh']
    return selected


def simulate_policy(policy, cell, replicate, phase, shared, initial_models, initial_thresholds,
                    contexts, initial_utilisation, truth, channels, domain, environment,
                    resources, heartbeat=None, origins=None, end_day=END_DAY,
                    refit=fit_observable):
    entries = initial_units(truth, channels, cell['level'], phase, replicate, end_day,
                             cell=cell['index'])
    mapping = domain.set_index('pn')
    for entry in entries:
        entry.update(scale=mapping.at[entry['pn'], 'scale'], family=mapping.at[entry['pn'], 'family'],
                     mh=float(resources[entry['pn']]), completed=[])
    initial_models = copy.deepcopy(initial_models)
    detector = DriftDetector(initial_models, domain.loc[domain.family.eq('rotor'), 'pn'], initial_utilisation)
    origins = list(origins) if origins is not None else list(pd.date_range('2024-01-01', '2025-12-01', freq='MS'))
    events, solver, fitted_history, fit_metadata, calibrations = [], [], [], [], []
    previous = {}
    for month, origin in enumerate(origins):
        origin = pd.Timestamp(origin)
        cutoff = (origin - START).days - 1
        stop = min(end_day, ((origins[month + 1] if month + 1 < len(origins) else
                             environment.date(end_day) + pd.Timedelta(days=1)) - START).days - 1)
        if heartbeat:
            heartbeat(stage='policy', policy=policy, month=month, origin=str(origin.date()))
        models = copy.deepcopy(initial_models)
        if policy in ('P2', 'P2_age') and month > 0:
            observations = policy_observations(entries, cutoff)
            spells, flights = training_inputs(shared, policy, observations, environment.flights)
            models, meta = refit(spells, flights, domain, origin, environment.minimum_days)
            fit_metadata.append(dict(origin=str(origin.date()), **meta))
        if policy == 'P3':
            for pn, model in models.items():
                example = next((e for e in entries if e['pn'] == pn), None)
                if example is not None:
                    factor = eta_factor(example['family'], cell['scenario'], cutoff, CHANGE_DAY, END_DAY)
                    model.update(beta=example['state'].beta, eta=example['eta'] * factor,
                                 nu=example['state'].nu, converged=True, fallback=None)
        if policy in ('P2', 'P2_age'):
            detector.observe(month, models, {ac: environment.observed_rate(ac, origin)
                                             for ac in environment.aircraft})
        fitted_history.append(dict(origin=str(origin.date()), parameters=copy.deepcopy(models)))
        thresholds = initial_thresholds
        if policy == 'P2_age' and month > 0:
            thresholds, diagnostic = calibrate_all(models, contexts, cell['r'], heartbeat)
            calibrations.append(dict(origin=str(origin.date()), diagnostics=diagnostic))
        if policy in ('P2', 'P2_fixed', 'P3'):
            schedule, diagnostic = planned_actions(entries, models, environment, origin,
                                                   cell['knowledge'], cell['r'], previous)
            solver.extend(diagnostic)
            previous = schedule
        else:
            schedule = {}
        for day in range(max(0, cutoff + 1), stop + 1):
            for entry in entries:
                state = entry['state']
                if day <= entry['start'] or state.time >= entry['end']:
                    continue
                finish = min(day, entry['end'])
                left = state.time
                rate = 1. if entry['scale'] == 'calendar' else environment.increment(entry['aircraft'], day)
                eta_left = entry['eta'] * eta_factor(entry['family'], cell['scenario'], left, CHANGE_DAY, END_DAY)
                eta_right = entry['eta'] * eta_factor(entry['family'], cell['scenario'],
                    np.nextafter(float(finish), float(left)), CHANGE_DAY, END_DAY)
                generated = state.advance(finish, rate, eta_left, eta_right)
                for event in generated:
                    if event['end'] >= entry['end']:
                        continue
                    entry['completed'].append(event)
                    coincident = (abs(event['end'] - round(event['end'])) < 1e-10 and
                                  round(event['end']) in environment.stops[entry['aircraft']])
                    cost = 1. if event['risk'] == 2 or coincident else cell['r']
                    events.append(dict(cohort='evaluation', policy=policy, unit=entry['unit'],
                        pn=entry['pn'], aircraft=entry['aircraft'], time=event['end'],
                        risk=event['risk'], cost=cost, mh=entry['mh'],
                        outside_visit=bool(event['risk'] == 1 and not coincident)))
            selected = (age_actions(entries, models, thresholds, environment, origin,
                                    cell['knowledge'], day, cell['r'])
                        if policy in ('P1', 'P2_age') else
                        set().union(*(v for (ac, when), v in schedule.items() if when == day)))
            for aircraft in environment.aircraft:
                active = [e for e in entries if e['aircraft'] == aircraft and e['start'] <= day <= e['end']]
                actual = [e for e in active if e['unit'] in selected]
                capacity = sum(e['mh'] for e in active) / 4
                if sum(e['mh'] for e in actual) > capacity + 1e-7:
                    raise RuntimeError('Executed policy violates preventive MH capacity')
                if actual and day not in environment.stops[aircraft]:
                    raise RuntimeError('Preventive outside an authorised visit')
                for entry in actual:
                    state = entry['state']
                    event = dict(start=state.birth, end=float(day), risk=3,
                                 renewal=state.renewal, age=state.age)
                    entry['completed'].append(event)
                    events.append(dict(cohort='evaluation', policy=policy, unit=entry['unit'],
                        pn=entry['pn'], aircraft=aircraft, time=float(day), risk=3,
                        cost=1., mh=entry['mh'], outside_visit=False))
                    state.renew(float(day))
    columns = ['cohort', 'policy', 'unit', 'pn', 'aircraft', 'time', 'risk', 'cost', 'mh', 'outside_visit']
    evaluated = evaluation_only(pd.DataFrame(events, columns=columns))
    return dict(policy=policy, cost=float(evaluated.cost.sum()),
        post_change_cost=float(evaluated.loc[evaluated.time.gt(CHANGE_DAY), 'cost'].sum()),
        events=events, unscheduled=int(evaluated.risk.eq(1).sum()),
        competing=int(evaluated.risk.eq(2).sum()), preventive=int(evaluated.risk.eq(3).sum()),
        outside_visit=int(evaluated.outside_visit.sum()), mh=float(evaluated.mh.sum()),
        solver=solver, parameter_history=fitted_history, fit_metadata=fit_metadata,
        calibration=calibrations, detection=detector.rows)


def run_replica(cell, replicate, phase, shared, truth, channels, domain, flights, stoppages,
                resources, heartbeat=None):
    environment = Environment(flights, stoppages, cell['scenario'])
    initial_spells, initial_clocks = shared.for_policy('P0')
    if heartbeat:
        heartbeat(stage='initial_fit')
    initial, metadata = fit_observable(initial_spells, initial_clocks, domain, START)
    contexts, utilisation = historical_calendars(initial_spells, initial_clocks, stoppages, domain, START)
    thresholds, calibration = calibrate_all(initial, contexts, cell['r'], heartbeat)
    results = [simulate_policy(policy, cell, replicate, phase, shared, initial, thresholds,
        contexts, utilisation, truth, channels, domain, environment, resources, heartbeat)
        for policy in POLICIES]
    return dict(policies=results, initial_fit=metadata, initial_calibration=calibration)
