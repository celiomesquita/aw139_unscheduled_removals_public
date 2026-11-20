"""Disposable one-reference processes, live-RSS admission and the original cutoff."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
from datetime import datetime,timezone
import json
import multiprocessing
from pathlib import Path
import signal
import time
import traceback
import psutil
from amendment015.state import ROOT,OUT,atomic,digest,freeze,ledger,utcnow

CUTOFF=datetime(2026,11,19,16,16,40,tzinfo=timezone.utc)
ALLOCATION=17662817894


class DeadlineReached(TimeoutError):pass


def admits(real_rss,new_estimate):
    return real_rss+new_estimate<=ALLOCATION


def process_rss():
    records={}
    for p in [psutil.Process()]+psutil.Process().children(recursive=True):
        try:
            if p.status()!=psutil.STATUS_ZOMBIE:
                records[str(p.pid)]=dict(rss_bytes=p.memory_info().rss,created=p.create_time())
        except psutil.NoSuchProcess:pass
    return records


def worker(item,attempt):
    from amendment015.readonly_progress import ReadOnlyProgress
    from amendment015.references import exact_job
    from amendment015.disk import disk_job
    name=item['id'];pid=os.getpid();started=utcnow().isoformat()
    atomic(OUT/'fresh_tasks'/f'{name}.json',dict(id=name,pid=pid,status='running',started_utc=started,
        attempt=attempt,storage='memmap' if name=='06' else 'RAM',process_reuse=False))
    checkpoint=OUT/'references'/f'{name}_checkpoint.json'
    record=json.loads(checkpoint.read_text());record.update(pid=pid,attempt=attempt,process_reuse=False)
    atomic(checkpoint,record)
    observer=ReadOnlyProgress(item);observer.start()
    complete=False
    try:
        if utcnow()>=CUTOFF:raise DeadlineReached('ORIGINAL_REFERENCE_CUTOFF')
        (disk_job if name=='06' else exact_job)(item)
        if utcnow()>CUTOFF:raise DeadlineReached('CERTIFICATE_FINISHED_AFTER_CUTOFF')
        complete=True
        atomic(OUT/'fresh_tasks'/f'{name}.json',dict(id=name,pid=pid,status='complete',started_utc=started,
            finished_utc=utcnow().isoformat(),attempt=attempt,storage='memmap' if name=='06' else 'RAM',
            certificate_sha256=digest(OUT/'references'/f'{name}_certificate.json'),process_reuse=False))
    except BaseException as error:
        atomic(OUT/'fresh_tasks'/f'{name}.json',dict(id=name,pid=pid,status='failed',started_utc=started,
            error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),attempt=attempt))
        raise
    finally:observer.stop(complete)


def verify_finished(config):
    completed=[]
    for item in config['sample']:
        path=OUT/'references'/f"{item['id']}_certificate.json"
        if not path.exists():continue
        cert=json.loads(path.read_text())
        if cert['status']!='complete' or cert['input_sha256']!=digest(OUT/'references'/f"{item['id']}_inputs.json"):
            raise RuntimeError('CERTIFICATE_INPUT_MISMATCH:'+item['id'])
        completed.append(item['id'])
    return completed


def run():
    from amendment015.references import check_sources
    config=json.loads((OUT/'configuration.json').read_text());check_sources(config)
    if config['memory_budget_bytes']!=ALLOCATION:raise RuntimeError('FROZEN_ALLOCATION_CHANGED')
    gate=json.loads((OUT/'disk_ready.json').read_text())
    for p,h in gate['sources'].items():
        if digest(ROOT/p)!=h:raise RuntimeError('STORAGE_IMPLEMENTATION_CHANGED:'+p)
    if utcnow()>=CUTOFF:raise DeadlineReached('ORIGINAL_REFERENCE_CUTOFF_ALREADY_REACHED')
    completed=verify_finished(config)
    if set(completed)!={'00','01','02','03','04','08'}:raise RuntimeError('UNEXPECTED_PRESERVED_CERTIFICATES')
    estimates={r['id']:r['estimated_bytes'] for r in json.loads((OUT/'memory_preflight.json').read_text())['contexts']}
    estimates['06']=gate['residual_ram_estimated_bytes']
    attempt=utcnow().strftime('%Y%m%dT%H%M%SZ')
    sources=[ROOT/'analysis/amendment015/fresh.py',ROOT/'analysis/amendment015/readonly_progress.py',ROOT/'analysis/amendment015_fresh.py',ROOT/'tests/test_amendment015_fresh.py']
    freeze(OUT/'fresh_configuration.json',dict(attempt=attempt,cutoff_utc=CUTOFF.isoformat(),allocation_bytes=ALLOCATION,
        workers_max=6,one_reference_per_process=True,reuse_workers=False,admission='real RSS of coordinator and all descendants + estimate of next task <= frozen allocation',
        task_order=['07','05','06'],estimates={k:estimates[k] for k in ['05','06','07']},telemetry_interval_seconds=120,
        telemetry_fraction_definition='built phase rows; swept finite visit breakpoints per phase with multiplicity',
        sources={str(p.relative_to(ROOT)):digest(p) for p in sources},original_configuration_sha256=digest(OUT/'configuration.json')))
    for name in ['05','06','07']:
        p=OUT/'references'/f'{name}_checkpoint.json'
        freeze(OUT/'fresh_attempt_history'/attempt/p.name,json.loads(p.read_text()))
    value=ledger('fresh_process_reference_resume')
    value.setdefault('author_decisions',[]).append(dict(recorded_utc=utcnow().isoformat(),decision='Resume 05/06/07 in new disposable processes; actual aggregate RSS admission; read-only telemetry; original cutoff; stop before calibration verification even if nine certified.'))
    value['technical_stop']=None;value['reference_effective_deadline_utc']=CUTOFF.isoformat()
    atomic(OUT/'time_ledger.json',value)
    pending=[next(x for x in config['sample'] if x['id']==name) for name in ['07','05','06']]
    live={};ctx=multiprocessing.get_context('spawn');stop_reason=None
    def kill_all():
        for p in live.values():
            if p.is_alive():p.kill()
    def expired(signum,frame):
        kill_all();raise DeadlineReached('ORIGINAL_REFERENCE_CUTOFF')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,max(.001,(CUTOFF-utcnow()).total_seconds()))
    started=time.perf_counter()
    try:
        while pending or live:
            if utcnow()>=CUTOFF:raise DeadlineReached('ORIGINAL_REFERENCE_CUTOFF')
            check_sources(config)
            for name,p in list(live.items()):
                if not p.is_alive():
                    p.join();code=p.exitcode;p.close();del live[name]
                    if code!=0:raise RuntimeError('REFERENCE_PROCESS_FAILED:'+name)
                    completed=verify_finished(config)
            rss=process_rss();total=sum(x['rss_bytes'] for x in rss.values())
            atomic(OUT/'fresh_resources.json',dict(utc=utcnow().isoformat(),rss_by_pid=rss,total_rss_bytes=total,allocation_bytes=ALLOCATION))
            if total>ALLOCATION:raise MemoryError('REAL_AGGREGATE_RSS_EXCEEDS_ALLOCATION')
            for item in list(pending):
                rss=process_rss();total=sum(x['rss_bytes'] for x in rss.values());need=estimates[item['id']]
                if len(live)<6 and admits(total,need):
                    p=ctx.Process(target=worker,args=(item,attempt),name='reference_'+item['id']);p.start()
                    live[item['id']]=p;pending.remove(item)
                    atomic(OUT/'fresh_admissions'/f"{item['id']}.json",dict(id=item['id'],pid=p.pid,utc=utcnow().isoformat(),
                        aggregate_rss_before_bytes=total,new_task_estimated_bytes=need,admission_sum_bytes=total+need,
                        allocation_bytes=ALLOCATION,process_reuse=False))
            atomic(OUT/'fresh_state.json',dict(status='running',utc=utcnow().isoformat(),completed=completed,
                active={name:p.pid for name,p in live.items()},pending=[x['id'] for x in pending],cutoff_utc=CUTOFF.isoformat(),
                consumed_this_attempt_seconds=time.perf_counter()-started,verification_started=False))
            ledger();time.sleep(.5)
        if len(verify_finished(config))!=9:raise RuntimeError('NINE_REFERENCES_NOT_CERTIFIED')
        records=[]
        for item in config['sample']:
            path=OUT/'references'/f"{item['id']}_certificate.json";cert=json.loads(path.read_text())
            records.append(dict(id=item['id'],certificate=path.name,sha256=digest(path),age=cert['age'],infinite=cert['infinite'],rate=cert['rate'],subdivisions=4,input_sha256=cert['input_sha256']))
        freeze(OUT/'references/manifest.json',dict(status='complete',N=9,seed=20261117015,
            configuration_sha256=digest(OUT/'configuration.json'),age_source_sha256=digest(ROOT/'analysis/amendment015/age.py'),references=records))
        from amendment015.age import require_manifest
        require_manifest(OUT/'references/manifest.json')
        ledger('nine_references_frozen_STOP_BEFORE_VERIFICATION')
        stop_reason='nine_references_certified'
    except BaseException as error:
        kill_all();stop_reason=type(error).__name__+':'+str(error)
        atomic(OUT/'fresh_stop.json',dict(utc=utcnow().isoformat(),reason=stop_reason,traceback=traceback.format_exc()))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        for name,p in live.items():
            if p.is_alive():p.kill()
            p.join(timeout=3)
            checkpoint=OUT/'references'/f'{name}_checkpoint.json';record=json.loads(checkpoint.read_text())
            if not (OUT/'references'/f'{name}_certificate.json').exists():
                record.update(status='interrupted',pid=p.pid,interrupted_utc=utcnow().isoformat(),reason=stop_reason)
                atomic(checkpoint,record)
            p.close()
        completed=verify_finished(config);value=ledger('fresh_references_STOP')
        summary=dict(status='STOP',reason=stop_reason,utc=utcnow().isoformat(),completed=completed,
            incomplete=[x['id'] for x in config['sample'] if x['id'] not in completed],
            progress={x['id']:json.loads((OUT/'fresh_progress'/f"{x['id']}.json").read_text()) for x in config['sample'] if (OUT/'fresh_progress'/f"{x['id']}.json").exists()},
            consumed_this_attempt_seconds=time.perf_counter()-started,global_consumed_seconds=value['consumed_seconds'],
            global_remaining_seconds=value['remaining_seconds'],reference_consumed_seconds=value['reference_consumed_seconds'],
            cutoff_utc=CUTOFF.isoformat(),verification_started=False,cheap_thresholds_computed=False,main_started=False)
        atomic(OUT/'fresh_state.json',summary)
        atomic(OUT/'state.json',summary)
    return 0 if stop_reason=='nine_references_certified' else 2
