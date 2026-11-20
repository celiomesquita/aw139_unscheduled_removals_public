"""Preparation and certified quarter-day reference searches, with hard deadlines."""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
import json
import math
import multiprocessing
from pathlib import Path
import time

import numpy as np
import pandas as pd
import psutil

from amendment015.state import ROOT, OUT, COMMIT, atomic, check_deadline, digest, freeze, ledger

SEED = 20261117015
FAMILIES = ('rotor','wheels','vests')


def diagnostic_json(value):
    """Represent unavailable diagnostics as null, never alter model parameters."""
    if isinstance(value, dict):
        return {str(k):diagnostic_json(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [diagnostic_json(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return diagnostic_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def source_snapshot():
    paths = list((ROOT/'analysis').glob('*.py')) + list((ROOT/'analysis/amendment015').glob('*.py'))
    paths += [ROOT/'tests/test_amendment015.py',ROOT/'analysis/emenda_A16_A9_015.md',ROOT/'requirements-lock.txt']
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}


def check_sources(config):
    for name,h in config['sources'].items():
        if digest(ROOT/name)!=h:
            raise RuntimeError('SOURCE_CHANGED_AFTER_FREEZE:'+name)


def prepare():
    ledger('reference_preparation',begin_references=True)
    check_deadline(references=True)
    path=OUT/'configuration.json'
    if path.exists():
        config=json.loads(path.read_text());check_sources(config)
        freeze(OUT/'configuration.sha256.json',dict(path='configuration.json',sha256=digest(path)))
        for item in config['sample']:
            freeze(OUT/'references'/f"{item['id']}_inputs.json",item)
        return config
    # Freeze memory allocation before loading the real auxiliary history.
    available=psutil.virtual_memory().available
    allocation=int(.70*available)
    from a9_warmup import SharedWarmup
    from a9_fitting import fit_observable
    from a9_environment import historical_calendars
    from a16_generator import START
    cohort=ROOT/'data/derived/a9/warmup/replicas/pilot_amplified_0000'
    required=[cohort/'manifest.json',cohort/'spells.csv',cohort/'flights.csv',
              ROOT/'config/a4_scale_map.csv',ROOT/'data/derived/stoppages.csv']
    for p in required:
        if not p.is_file():raise FileNotFoundError('REQUIRED_REFERENCE_INPUT_ABSENT:'+str(p.relative_to(ROOT)))
    shared=SharedWarmup(cohort)
    spells,flights=shared.for_policy('P0')
    domain=pd.read_csv(ROOT/'config/a4_scale_map.csv')
    models,metadata=fit_observable(spells,flights,domain,START)
    check_deadline(references=True)
    contexts,_=historical_calendars(spells,flights,pd.read_csv(ROOT/'data/derived/stoppages.csv'),domain,START)
    serial_contexts={pn:[dict(daily=np.asarray(c['daily'],float).tolist(),
        visits=[int(x) for x in c['visits']],weight=int(c['weight'])) for c in values]
        for pn,values in contexts.items()}
    rng=np.random.Generator(np.random.PCG64(SEED));sample=[]
    for r in (2,5,10):
        for family in FAMILIES:
            pns=sorted(domain.loc[domain.family.eq(family),'pn'])
            pn=pns[int(rng.integers(len(pns)))]
            model=models[pn]
            if not model['converged']:
                raise RuntimeError('SELECTED_REFERENCE_MODEL_UNAVAILABLE:'+pn)
            sample.append(dict(id=f'{len(sample):02d}',pn=pn,r=r,family=family,
                               model=model,contexts=serial_contexts[pn]))
    value=dict(commit=COMMIT,amendment_sha256=digest(ROOT/'analysis/emenda_A16_A9_015.md'),
        seed=SEED,N=9,subdivisions=4,R=200,cells=72,policies=6,workers_max=6,native_threads=1,
        memory_available_bytes_at_preparation=available,memory_budget_bytes=allocation,
        sources=source_snapshot(),inputs={str(p.relative_to(ROOT)):digest(p) for p in required},
        initial_models=models,sample=sample,initial_fit=diagnostic_json(metadata),
        unavailable_diagnostic_encoding='null',
        input_free_text_exported=False,cheap_thresholds_computed=False)
    freeze(path,value)
    freeze(OUT/'configuration.sha256.json',dict(path='configuration.json',sha256=digest(path)))
    for item in sample:
        freeze(OUT/'references'/f"{item['id']}_inputs.json",item)
    ledger('reference_memory_preflight')
    return value


def memory_preflight(config):
    from a9_parallel import estimated_grid_bytes
    rows=[]
    for item in config['sample']:
        model=item['model']
        need=estimated_grid_bytes(model,item['contexts'],4) if model['beta']>1 else 0
        rows.append(dict(id=item['id'],pn=item['pn'],r=item['r'],family=item['family'],
            estimated_bytes=need,allocation_bytes=config['memory_budget_bytes'],
            fits_allocation=need<=config['memory_budget_bytes'],subdivisions=4))
    atomic(OUT/'memory_preflight.json',dict(contexts=rows,resolution_reduced=False,
        all_fit=all(r['fits_allocation'] for r in rows)))
    for row in rows:
        checkpoint=OUT/'references'/f"{row['id']}_checkpoint.json"
        if not checkpoint.exists():
            atomic(checkpoint,dict(id=row['id'],pn=row['pn'],r=row['r'],status='pending',
                input_sha256=digest(OUT/'references'/f"{row['id']}_inputs.json"),estimated_bytes=row['estimated_bytes']))
    failures=[r for r in rows if not r['fits_allocation']]
    if failures:
        raise MemoryError('QUARTER_DAY_REFERENCE_EXCEEDS_FROZEN_70_PERCENT_ALLOCATION:'+failures[0]['id'])
    # The old evaluator certifies infinite age for beta<=1 but does not return
    # its cost rate; never invent that required manifest value.
    if any(x['model']['beta']<=1 for x in config['sample']):
        raise RuntimeError('EXACT_INFINITE_BRANCH_RATE_NOT_EXPOSED_BY_HISTORICAL_EVALUATOR')
    return {row['id']:row['estimated_bytes'] for row in rows}


def exact_job(item):
    from a9_static_fast import exhaustive_threshold
    check_deadline(references=True,refresh=False)
    name=item['id'];checkpoint=OUT/'references'/f'{name}_checkpoint.json'
    before=json.loads(checkpoint.read_text());before.update(status='running',started_utc=datetime.now().astimezone().isoformat())
    atomic(checkpoint,before)
    wall,cpu=time.perf_counter(),time.process_time()
    model=item['model']
    age,diagnostics=exhaustive_threshold(item['contexts'],model['beta'],model['eta'],model['nu'],item['r'],4)
    # Same historical evaluator, no change in parameters, grid or tolerances.
    check_deadline(references=True,refresh=False)
    rate=diagnostics.get('expected_rate_variable_groups')
    if not diagnostics.get('global_discrete_search') or rate is None or not math.isfinite(rate):
        raise ArithmeticError('EXACT_REFERENCE_NOT_CERTIFIED')
    certificate=dict(id=name,pn=item['pn'],r=item['r'],status='complete',
        input_sha256=digest(OUT/'references'/f'{name}_inputs.json'),subdivisions=4,
        configuration_sha256=digest(OUT/'configuration.json'),
        evaluator_sha256={p:digest(ROOT/p) for p in ('analysis/a9_static.py','analysis/a9_static_fast.py')},
        age=None if math.isinf(age) else age,infinite=math.isinf(age),rate=rate,
        diagnostics=diagnostics,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
        final_rss_bytes=psutil.Process().memory_info().rss)
    path=OUT/'references'/f'{name}_certificate.json';freeze(path,certificate)
    before.update(status='complete',certificate=path.name,certificate_sha256=digest(path));atomic(checkpoint,before)
    return name


def calculate():
    config=prepare();check_sources(config);needs=memory_preflight(config)
    ledger('exact_references')
    pending_items=[];complete=[]
    for item in config['sample']:
        path=OUT/'references'/f"{item['id']}_certificate.json"
        if path.exists():
            cert=json.loads(path.read_text())
            if cert['input_sha256']!=digest(OUT/'references'/f"{item['id']}_inputs.json") or cert['status']!='complete':
                raise RuntimeError('REFERENCE_CERTIFICATE_INCOMPATIBLE')
            complete.append(item['id'])
        else:pending_items.append(item)
    pool=ProcessPoolExecutor(max_workers=6,mp_context=multiprocessing.get_context('spawn'))
    running={}
    try:
        while pending_items or running:
            check_deadline(references=True);check_sources(config)
            processes=[psutil.Process()]+psutil.Process().children(recursive=True)
            rss={str(p.pid):p.memory_info().rss for p in processes if p.is_running()}
            if sum(rss.values())>config['memory_budget_bytes']:
                raise MemoryError('AGGREGATE_RSS_EXCEEDS_FROZEN_MEMORY_ALLOCATION')
            used=sum(needs[item['id']] for item in running.values())
            for item in list(pending_items):
                need=needs[item['id']]
                if len(running)<6 and used+need<=config['memory_budget_bytes']:
                    running[pool.submit(exact_job,item)]=item;pending_items.remove(item);used+=need
            if not running and pending_items:
                raise MemoryError('NO_REFERENCE_JOB_FITS_WITHOUT_REDUCING_GRID')
            done,_=wait(running,timeout=5,return_when=FIRST_COMPLETED)
            for future in done:
                item=running.pop(future);future.result();complete.append(item['id'])
            atomic(OUT/'reference_progress.json',dict(status='running',completed=sorted(complete),
                pending=sorted([x['id'] for x in pending_items]+[x['id'] for x in running.values()]),
                estimated_active_bytes=sum(needs[x['id']] for x in running.values()),
                rss_by_pid=rss,aggregate_rss_bytes=sum(rss.values()),
                updated_utc=datetime.now().astimezone().isoformat()))
        pool.shutdown(wait=True)
    except BaseException:
        pool.terminate_workers();raise
    records=[]
    for item in config['sample']:
        path=OUT/'references'/f"{item['id']}_certificate.json"
        certificate=json.loads(path.read_text())
        records.append(dict(id=item['id'],certificate=path.name,sha256=digest(path),
            age=certificate['age'],infinite=certificate['infinite'],
            rate=certificate['rate'],subdivisions=4,input_sha256=certificate['input_sha256']))
    manifest=dict(status='complete',N=9,seed=SEED,configuration_sha256=digest(OUT/'configuration.json'),
                  age_source_sha256=digest(ROOT/'analysis/amendment015/age.py'),references=records)
    freeze(OUT/'references/manifest.json',manifest)
    from amendment015.age import require_manifest
    require_manifest(OUT/'references/manifest.json')
    ledger('references_frozen')
    return manifest


def stop_state(error):
    value=ledger('technical_stop',stop=dict(code=type(error).__name__,message=str(error)))
    completed=[];pending=[];checkpoints=[]
    for p in sorted((OUT/'references').glob('*_checkpoint.json')):
        data=json.loads(p.read_text());checkpoints.append(str(p.relative_to(ROOT)))
        (completed if data['status']=='complete' else pending).append(data['id'])
    state=dict(status='STOP',error_type=type(error).__name__,error_code=str(error),
        completed=completed,pending=pending,checkpoints=checkpoints,
        global_consumed_seconds=value['consumed_seconds'],global_remaining_seconds=value['remaining_seconds'],
        reference_consumed_seconds=value.get('reference_consumed_seconds'),
        reference_remaining_seconds=value.get('reference_remaining_seconds'),
        cheap_thresholds_computed=False,verification_executed=False,profiling_executed=False)
    atomic(OUT/'state.json',state)
    return state
