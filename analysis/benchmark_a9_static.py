"""Paired computational kernels; these timings never select experimental R."""
import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import heapq
import importlib.util
import time

import numpy as np
import pandas as pd

from a16_generator import ROOT, START, sha
from a9_environment import historical_calendars
from a9_fitting import fit_observable
from a9_static_fast import FastCalendarRenewal
from a9_warmup import SharedWarmup
from round5_execution import atomic_json

ARCHIVE = ROOT / 'analysis/audit/amendment012/before_optimisation/analysis/a9_static.py'
spec = importlib.util.spec_from_file_location('static_before_amendment012', ARCHIVE)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def exercise(factory, daily, visits, beta, eta, nu, r, operations):
    start = time.perf_counter()
    model = factory(daily, visits, beta, eta, nu, r)
    setup = time.perf_counter() - start
    heap = [(model.next_breakpoint(phase), phase) for phase in range(model.n)]
    heapq.heapify(heap)
    start = time.perf_counter()
    steps = []
    for _ in range(operations):
        age, phase = heapq.heappop(heap)
        if not np.isfinite(age):
            break
        model.extend(phase)
        steps.append((age, phase))
        heapq.heappush(heap, (model.next_breakpoint(phase), phase))
    seconds = time.perf_counter() - start
    return model, steps, dict(setup_seconds=setup, update_seconds=seconds,
                              complete_calibration=False, update_operations=len(steps))


def main():
    started = time.perf_counter()
    shared = SharedWarmup(ROOT / 'data/derived/a9/warmup/replicas/pilot_amplified_0000')
    spells, flights = shared.for_policy('P0')
    domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
    models, _ = fit_observable(spells, flights, domain, START)
    contexts, _ = historical_calendars(spells, flights,
        pd.read_csv(ROOT / 'data/derived/stoppages.csv'), domain, START)
    pn = '3G3240A07531'
    context = next(c for c in contexts[pn] if np.sum(c['daily']) > 0 and len(c['visits']))
    model = models[pn]
    arguments = (context['daily'], context['visits'], model['beta'], model['eta'], model['nu'], 10., 8192)
    print('Paired annual-calendar benchmark: reference, then equivalent optimisation', flush=True)
    before, before_steps, a = exercise(legacy.CalendarRenewal, *arguments)
    after, after_steps, b = exercise(FastCalendarRenewal, *arguments)
    if before_steps != after_steps:
        raise RuntimeError('Optimisation changed the age-breakpoint sequence')
    np.testing.assert_allclose(after.P, before.P, rtol=0, atol=1e-10)
    np.testing.assert_allclose(after.stationary, before.stationary, rtol=0, atol=1e-8)
    np.testing.assert_allclose(after.cost, before.cost, rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(after.duration, before.duration, rtol=1e-10, atol=1e-9)
    if abs(after.rate() - before.rate()) > 1e-9:
        raise RuntimeError('Expected renewal rate differs between paired kernels')
    result = dict(pn=pn, same_saved_pilot_history=True, phase_count=after.n,
        reference=a, optimised=b, update_speedup=a['update_seconds'] / b['update_seconds'],
        total_speedup=(a['setup_seconds'] + a['update_seconds']) /
                      (b['setup_seconds'] + b['update_seconds']),
        probability_matrix_max_difference=float(np.max(np.abs(after.P - before.P))),
        stationary_max_difference=float(np.max(np.abs(after.stationary - before.stationary))),
        renewal_rate_absolute_difference=abs(after.rate() - before.rate()),
        full_refactors_optimised=after.full_refactors, sparse_products=after.sparse_products,
        full_pilot_measured=False, R_selected=False, whole_benchmark_wall_seconds=time.perf_counter() - started,
        sources={str(ARCHIVE.relative_to(ROOT)): sha(ARCHIVE),
                 'analysis/a9_static_fast.py': sha(ROOT / 'analysis/a9_static_fast.py')})
    atomic_json(ROOT / 'data/derived/a9/optimisation/kernel_benchmark.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
