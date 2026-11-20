"""Bounded independent P/N calibrations; no random draws or scientific changes."""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import multiprocessing
import os
import time
import math

import numpy as np
import psutil
from scipy.special import gamma, gammaincc

from a9_static_fast import calibrate_threshold, exhaustive_threshold


def _calibrate(pn, model, contexts, r):
    start = time.perf_counter()
    age, diagnostics = calibrate_threshold(contexts, model['beta'], model['eta'], model['nu'], r)
    return pn, age, diagnostics, dict(pid=os.getpid(), wall_seconds=time.perf_counter() - start)


def _grid(pn, model, contexts, r, subdivision):
    start = time.perf_counter()
    age, diagnostic = exhaustive_threshold(contexts, model['beta'], model['eta'], model['nu'], r, subdivision)
    return pn, subdivision, age, diagnostic, dict(pid=os.getpid(), wall_seconds=time.perf_counter() - start)


def estimated_grid_bytes(model, contexts, subdivision):
    """Conservative array estimate for the current grid, not a reduced precision."""
    estimate = 0
    beta, eta, nu = model['beta'], model['eta'], model['nu']
    for context in contexts:
        daily = np.asarray(context['daily'], float)
        if not context['visits'] or daily.sum() == 0:
            continue
        period, total, repeats = len(daily), np.repeat(daily / subdivision, subdivision).sum(), 1
        while True:
            exposure, elapsed = repeats * total, repeats * period
            probability = math.exp(-(exposure / eta) ** beta - nu * elapsed)
            bound = (probability / nu if nu else period * (probability +
                eta * gamma(1 / beta) * gammaincc(1 / beta, (exposure / eta) ** beta) / beta / total))
            if probability <= 1e-10 and bound <= 1e-7:
                break
            repeats *= 2
            if repeats > 65536:
                raise ArithmeticError('Static calibration tail could not be bounded')
        n, length = period * subdivision, period * subdivision * repeats
        constant = bool(np.all(daily == daily[0]))
        kernels = 1 if constant else n
        estimate += 8 * (6 * (length + 1) * kernels + 6 * n * n +
                         n * (repeats + 1) * len(context['visits']) + 80 * (length + 1))
    return max(estimate, 1024 ** 2)


class CalibrationExecutor:
    def __init__(self, workers=6, memory_budget_bytes=None):
        self.workers = workers
        self.pool = None
        self.timings = []
        self.memory_budget_bytes = memory_budget_bytes or int(psutil.virtual_memory().available * .7)

    def __enter__(self):
        for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            os.environ[name] = '1'
        if self.workers > 1:
            self.pool = ProcessPoolExecutor(max_workers=self.workers,
                mp_context=multiprocessing.get_context('spawn'))
        return self

    def calibrate(self, models, contexts, r, heartbeat=None):
        results, pending, ready, histories = {}, {}, [], {}
        for pn in sorted(models):
            model = models[pn]
            if not model['converged'] or not contexts.get(pn):
                results[pn] = (float('inf'), dict(reason='initial_model_or_calendar_unavailable'))
            elif self.pool and model['beta'] > 1:
                ready.append((pn, 1))
                histories[pn] = []
            else:
                key, age, diagnostic, timing = _calibrate(pn, model, contexts[pn], r)
                results[key] = age, diagnostic
                self.timings.append(dict(pn=pn, **timing))
        last_heartbeat = 0.
        while ready or pending:
            used = sum(item[2] for item in pending.values())
            for pn, subdivision in sorted(ready):
                if len(pending) >= self.workers:
                    break
                need = estimated_grid_bytes(models[pn], contexts[pn], subdivision)
                if used + need > self.memory_budget_bytes:
                    continue
                future = self.pool.submit(_grid, pn, models[pn], contexts[pn], r, subdivision)
                pending[future] = pn, subdivision, need
                ready.remove((pn, subdivision))
                used += need
            if not pending:
                raise MemoryError('P1 grid requires more memory than the frozen calibration allocation')
            if heartbeat and time.perf_counter() - last_heartbeat >= 5:
                heartbeat(stage='P1_calibration_parallel', pending_pns=sorted(p[0] for p in pending.values()),
                          calibration_workers=len(pending), estimated_calibration_bytes=used)
                last_heartbeat = time.perf_counter()
            done, _ = wait(pending, timeout=1., return_when=FIRST_COMPLETED)
            for future in done:
                pn, subdivision, need = pending.pop(future)
                key, grid, age, diagnostic, timing = future.result()
                self.timings.append(dict(pn=pn, subdivisions=subdivision, estimated_bytes=need, **timing))
                previous = histories[pn][-1].get('expected_rate_variable_groups') if histories[pn] else None
                histories[pn].append(diagnostic)
                value = diagnostic.get('expected_rate_variable_groups')
                if value is None or (previous is not None and abs(value - previous) <= 1e-4 + 1e-3 * abs(value)):
                    results[pn] = age, dict(refinements=histories[pn], converged=True)
                elif subdivision < 4:
                    ready.append((pn, 2 * subdivision))
                else:
                    raise ArithmeticError('P1 phase refinement did not meet fixed cost-rate tolerance')
        # Stable scientific output order, independent of worker completion order.
        return ({pn: results[pn][0] for pn in sorted(results)},
                {pn: results[pn][1] for pn in sorted(results)})

    def __exit__(self, kind, value, traceback):
        if self.pool is not None:
            if kind is not None:
                self.pool.terminate_workers()
            else:
                self.pool.shutdown(wait=True)
