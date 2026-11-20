"""One author-authorised isolated execution of context 06; numerical code unchanged."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import hashlib
import json
import math
from pathlib import Path
import signal
import threading
import time
import traceback
from datetime import datetime
from unittest.mock import patch
from amendment015.state import ROOT,OUT,END,atomic,digest,freeze,ledger,utcnow

RUN=OUT/'additional06'


def prefix_matches(data,length,expected):
    return hashlib.sha256(data[:length]).hexdigest()==expected


def integrity(config,authorisation):
    for name,h in config['sources'].items():
        data=(ROOT/name).read_bytes()
        if name=='analysis/emenda_A16_A9_015.md':
            if not prefix_matches(data,authorisation['original_amendment_prefix_bytes'],h):
                raise RuntimeError('COMMITTED_AMENDMENT_PREFIX_CHANGED')
            if hashlib.sha256(data).hexdigest()!=authorisation['appended_amendment_sha256']:
                raise RuntimeError('APPENDED_AMENDMENT_CHANGED')
        elif hashlib.sha256(data).hexdigest()!=h:raise RuntimeError('NUMERICAL_SOURCE_CHANGED:'+name)
    for name,h in json.loads((OUT/'disk_ready.json').read_text())['sources'].items():
        if digest(ROOT/name)!=h:raise RuntimeError('TESTED_MEMMAP_SOURCE_CHANGED:'+name)
    for name,h in authorisation['preserved_certificates'].items():
        if digest(OUT/'references'/f'{name}_certificate.json')!=h:
            raise RuntimeError('PRESERVED_CERTIFICATE_CHANGED:'+name)
    if digest(OUT/'configuration.json')!=authorisation['numeric_configuration_sha256']:
        raise RuntimeError('NUMERIC_CONFIGURATION_CHANGED')


def run():
    # The preparation start is immutable and was recorded before this launcher existed.
    value=json.loads((OUT/'time_ledger.json').read_text());a=value['additional06']
    begin=datetime.fromisoformat(a['preparation_start_utc']);deadline=datetime.fromisoformat(a['deadline_utc'])
    if utcnow()>=deadline:raise TimeoutError('ADDITIONAL06_PREPARATION_WINDOW_EXPIRED')
    if (RUN/'launch.json').exists():raise RuntimeError('SINGLE_ADDITIONAL_EXECUTION_ALREADY_LAUNCHED')
    # Default OS signal action enforces the hard limit even inside a long native call.
    signal.signal(signal.SIGALRM,signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL,(deadline-utcnow()).total_seconds())
    import psutil
    import shutil
    import amendment015.disk as disk
    from amendment015.readonly_progress import ReadOnlyProgress
    config=json.loads((OUT/'configuration.json').read_text());integrity(config,a)
    item=next(x for x in config['sample'] if x['id']=='06')
    if item!=json.loads((OUT/'references/06_inputs.json').read_text()):raise RuntimeError('FROZEN_CONTEXT06_INPUT_CHANGED')
    if (OUT/'references/06_certificate.json').exists():raise RuntimeError('CONTEXT06_ALREADY_CERTIFIED')
    proc=psutil.Process()
    if proc.children(recursive=True):raise RuntimeError('ADDITIONAL_EXECUTOR_PROCESS_PRESENT')
    estimate=disk.resource_estimate(item);free=shutil.disk_usage(OUT/'scratch').free
    if estimate['disk_estimated_bytes']+2*1024**3>free:raise OSError('ADDITIONAL06_DISK_CAPACITY_INSUFFICIENT')
    if proc.memory_info().rss+estimate['residual_ram_estimated_bytes']>config['memory_budget_bytes']:
        raise MemoryError('ADDITIONAL06_RAM_PREFLIGHT_FAILED')
    RUN.mkdir(parents=True,exist_ok=True)
    preserved={name:dict(sha256=h,mtime_ns=(OUT/'references'/f'{name}_certificate.json').stat().st_mtime_ns)
               for name,h in a['preserved_certificates'].items()}
    specification=dict(preparation_start_utc=begin.isoformat(),deadline_utc=deadline.isoformat(),cap_seconds=28800,
        single_execution=True,start_from_zero=True,python_processes=1,pid=os.getpid(),child_processes=0,
        native_threads=1,telemetry_interval_seconds=120,
        original_numeric_configuration_sha256=digest(OUT/'configuration.json'),
        original_context06_input_sha256=digest(OUT/'references/06_inputs.json'),
        tested_memmap_source_sha256=digest(ROOT/'analysis/amendment015/disk.py'),
        unchanged_readonly_telemetry_sha256=digest(ROOT/'analysis/amendment015/readonly_progress.py'),
        controller_source_sha256=digest(__file__),preserved_certificates=preserved,
        amended_document_sha256=digest(ROOT/'analysis/emenda_A16_A9_015.md'),
        clock_only_deviation='tested disk module deadline callback uses this authorised 8h window; numerical evaluator functions unchanged',
        resources=dict(**estimate,free_disk_bytes=free,allocation_bytes=config['memory_budget_bytes']))
    freeze(RUN/'configuration.json',specification)
    initial=dict(status='running',pid=os.getpid(),calculation_started_utc=utcnow().isoformat(),
        preparation_start_utc=begin.isoformat(),deadline_utc=deadline.isoformat(),single_execution=True)
    descriptor=os.open(RUN/'launch.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as f:json.dump(initial,f,sort_keys=True,indent=2);f.write('\n')
    atomic(RUN/'checkpoint.json',dict(initial,input_sha256=digest(OUT/'references/06_inputs.json'),
        storage='memmap',restart_partial_state=False))
    value=ledger('additional06_isolated_calculation');value['additional06'].update(status='running',pid=os.getpid(),
        calculation_started_utc=initial['calculation_started_utc'],configuration_sha256=digest(RUN/'configuration.json'))
    atomic(OUT/'time_ledger.json',value)
    stop=threading.Event();resource_error=[]
    def authorised_clock(**kwargs):
        if utcnow()>=min(deadline,END):raise TimeoutError('ADDITIONAL06_HARD_DEADLINE')
    def monitor():
        last_ledger=0.
        try:
            while not stop.wait(2.):
                rss=proc.memory_info().rss;children=proc.children(recursive=True)
                atomic(RUN/'resources.json',dict(utc=utcnow().isoformat(),pid=os.getpid(),rss_bytes=rss,
                    cpu_user_system_seconds=sum(proc.cpu_times()[:2]),children=[p.pid for p in children],
                    allocation_bytes=config['memory_budget_bytes']))
                if children:raise RuntimeError('ANOTHER_EXECUTOR_PROCESS_PRESENT')
                if rss>config['memory_budget_bytes']:raise MemoryError('ISOLATED_RSS_EXCEEDS_ALLOCATION')
                if time.monotonic()-last_ledger>=60:
                    integrity(config,a)
                    current=ledger();current['additional06'].update(
                        elapsed_seconds=(utcnow()-begin).total_seconds(),remaining_seconds=max(0.,(deadline-utcnow()).total_seconds()))
                    atomic(OUT/'time_ledger.json',current);last_ledger=time.monotonic()
        except BaseException as error:
            resource_error.append(str(error))
            atomic(RUN/'failure.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
            os.kill(os.getpid(),signal.SIGTERM)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    observer=ReadOnlyProgress(item,path=RUN/'progress.json');observer.start()
    wall,cpu=time.perf_counter(),time.process_time();complete=False
    try:
        # Only the expired deadline check is replaced. Array, search and arithmetic code are identical.
        with patch.object(disk,'check_deadline',authorised_clock):
            age,diagnostics=disk.disk_threshold(item['contexts'],item['model']['beta'],item['model']['eta'],
                item['model']['nu'],item['r'],4)
        authorised_clock()
        rate=diagnostics.get('expected_rate_variable_groups')
        if not diagnostics.get('global_discrete_search') or rate is None or not math.isfinite(rate):
            raise ArithmeticError('ADDITIONAL06_REFERENCE_NOT_CERTIFIED')
        stop.set();thread.join();observer.stop(True)
        integrity(config,a)
        certificate=dict(id='06',pn=item['pn'],r=item['r'],status='complete',pid=os.getpid(),
            input_sha256=digest(OUT/'references/06_inputs.json'),subdivisions=4,
            configuration_sha256=digest(OUT/'configuration.json'),
            evaluator_sha256={p:digest(ROOT/p) for p in ('analysis/a9_static.py','analysis/a9_static_fast.py')},
            storage_source_sha256=digest(ROOT/'analysis/amendment015/disk.py'),
            equivalence_sha256=digest(OUT/'disk_equivalence.json'),additional_execution_configuration_sha256=digest(RUN/'configuration.json'),
            age=None if math.isinf(age) else age,infinite=math.isinf(age),rate=rate,diagnostics=diagnostics,
            wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
            elapsed_since_preparation_seconds=(utcnow()-begin).total_seconds(),finished_utc=utcnow().isoformat(),
            final_rss_bytes=proc.memory_info().rss)
        authorised_clock();freeze(OUT/'references/06_certificate.json',certificate)
        records=[]
        for case in config['sample']:
            path=OUT/'references'/f"{case['id']}_certificate.json";c=json.loads(path.read_text())
            if c['status']!='complete' or c['input_sha256']!=digest(OUT/'references'/f"{case['id']}_inputs.json"):
                raise RuntimeError('NINE_REFERENCE_INPUT_MISMATCH')
            records.append(dict(id=case['id'],certificate=path.name,sha256=digest(path),age=c['age'],infinite=c['infinite'],
                rate=c['rate'],subdivisions=4,input_sha256=c['input_sha256']))
        authorised_clock()
        freeze(OUT/'references/manifest.json',dict(status='complete',N=9,seed=20261117015,
            configuration_sha256=digest(OUT/'configuration.json'),age_source_sha256=digest(ROOT/'analysis/amendment015/age.py'),
            references=records,additional06_configuration_sha256=digest(RUN/'configuration.json')))
        from amendment015.age import require_manifest
        require_manifest(OUT/'references/manifest.json');integrity(config,a);authorised_clock()
        complete=True
        signal.setitimer(signal.ITIMER_REAL,0)
        atomic(RUN/'checkpoint.json',dict(initial,status='complete',finished_utc=utcnow().isoformat(),
            certificate_sha256=digest(OUT/'references/06_certificate.json'),manifest_sha256=digest(OUT/'references/manifest.json')))
        current=ledger('additional06_certified_STOP_BEFORE_VERIFICATION')
        current['additional06'].update(status='complete',finished_utc=utcnow().isoformat(),
            elapsed_seconds=(utcnow()-begin).total_seconds(),manifest_sha256=digest(OUT/'references/manifest.json'))
        current['references_certified']=9;current['references_pending']=[]
        atomic(OUT/'time_ledger.json',current)
        atomic(RUN/'state.json',dict(status='STOP_FOR_AUDIT',complete_references=9,verification_started=False,
            global_consumed_seconds=current['consumed_seconds'],global_remaining_seconds=current['remaining_seconds']))
    except BaseException as error:
        stop.set();thread.join();observer.stop(False)
        atomic(RUN/'failure.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        raise
    finally:
        if complete:signal.setitimer(signal.ITIMER_REAL,0)

if __name__=='__main__':run()
