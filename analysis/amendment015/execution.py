"""New P1/P2_age adapter; the historical policy and simulator sources stay intact."""
from concurrent.futures import ProcessPoolExecutor
import math
import multiprocessing
import os
import time

from amendment015.age import calibrate, require_manifest
from amendment015.state import OUT, check_deadline


def age_job(pn, model, contexts, r, manifest):
    wall, cpu = time.perf_counter(), time.process_time()
    age, diagnostic = calibrate(contexts, model['beta'], model['eta'], model['nu'], r,
                                manifest_path=manifest)
    return pn, age, diagnostic, dict(pid=os.getpid(),
        wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu)


class AgeCalibrationExecutor:
    def __init__(self, workers=6, manifest=OUT/'references/manifest.json'):
        if not 1 <= workers <= 6:
            raise ValueError('SIX_WORKERS_PLUS_COORDINATOR_AND_RESOURCE_TRACKER')
        self.workers, self.manifest = workers, manifest
        self.pool, self.timings = None, []

    def __enter__(self):
        require_manifest(self.manifest)
        if any(os.environ.get(key) != '1' for key in
               ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')):
            raise RuntimeError('NATIVE_THREADS_MUST_BE_ONE_BEFORE_SCIENTIFIC_IMPORTS')
        if self.workers > 1:
            self.pool = ProcessPoolExecutor(max_workers=self.workers,
                mp_context=multiprocessing.get_context('spawn'))
        return self

    def calibrate(self, models, contexts, r, heartbeat=None):
        require_manifest(self.manifest)
        results, jobs = {}, {}
        for pn in sorted(models):
            check_deadline()
            if not models[pn]['converged'] or not contexts.get(pn):
                results[pn] = math.inf, dict(reason='initial_model_or_calendar_unavailable')
                continue
            if heartbeat:
                heartbeat(stage='age_calibration', pn=pn)
            args = pn, models[pn], contexts[pn], r, self.manifest
            if self.pool:
                jobs[pn] = self.pool.submit(age_job, *args)
            else:
                key, age, diagnostic, timing = age_job(*args)
                results[key] = age, diagnostic
                self.timings.append(dict(pn=key, **timing))
        for pn in sorted(jobs):
            check_deadline()
            key, age, diagnostic, timing = jobs[pn].result()
            results[key] = age, diagnostic
            self.timings.append(dict(pn=key, **timing))
        return ({pn:results[pn][0] for pn in sorted(results)},
                {pn:results[pn][1] for pn in sorted(results)})

    def __exit__(self, kind, value, traceback):
        if self.pool:
            if kind:
                self.pool.terminate_workers()
            else:
                self.pool.shutdown(wait=True)


def run_replica(cell, replicate, phase, shared, truth, channels, domain, flights,
                stoppages, resources, heartbeat=None, workers=6,
                manifest=OUT/'references/manifest.json'):
    """Use the unchanged six policies, replacing only their age-calibration adapter."""
    require_manifest(manifest)
    from a16_generator import START
    from a9_environment import Environment, historical_calendars
    from a9_fitting import fit_observable
    from a9_simulation import calibrate_all, simulate_policy
    from a9_warmup import POLICIES
    environment = Environment(flights, stoppages, cell['scenario'])
    initial_spells, initial_clocks = shared.for_policy('P0')
    if heartbeat:
        heartbeat(stage='initial_fit')
    initial, metadata = fit_observable(initial_spells, initial_clocks, domain, START)
    contexts, utilisation = historical_calendars(initial_spells, initial_clocks, stoppages, domain, START)
    with AgeCalibrationExecutor(workers, manifest) as executor:
        thresholds, calibration = calibrate_all(initial, contexts, cell['r'], heartbeat, executor)
        results = [simulate_policy(policy, cell, replicate, phase, shared, initial, thresholds,
            contexts, utilisation, truth, channels, domain, environment, resources, heartbeat,
            calibration_executor=executor) for policy in POLICIES]
    return dict(policies=results, initial_fit=metadata, initial_calibration=calibration,
                calibration_execution=executor.timings)
