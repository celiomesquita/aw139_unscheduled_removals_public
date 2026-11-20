"""Author-authorised RAM jobs, then equivalence-gated disk reference 06."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
import time
import psutil
from amendment015.state import OUT,ROOT,atomic,ledger,check_deadline,digest,freeze,utcnow
from amendment015.references import check_sources,exact_job,stop_state


def main():
    config=json.loads((OUT/'configuration.json').read_text());check_sources(config)
    needs={x['id']:x['estimated_bytes'] for x in json.loads((OUT/'memory_preflight.json').read_text())['contexts']}
    pending=[x for x in config['sample'] if x['id']!='06' and not (OUT/'references'/f"{x['id']}_certificate.json").exists()]
    complete=[x['id'] for x in config['sample'] if (OUT/'references'/f"{x['id']}_certificate.json").exists()]
    ledger('authorised_reference_resume')
    pool=ProcessPoolExecutor(max_workers=6,mp_context=multiprocessing.get_context('spawn'))
    running={}; disk_submitted='06' in complete
    try:
        while pending or running or not disk_submitted:
            check_deadline(references=True);check_sources(config)
            failure=OUT/'disk_failure.json'
            if failure.exists():raise RuntimeError('DISK_EQUIVALENCE_OR_PREFLIGHT_FAILED:'+failure.read_text())
            ready=OUT/'disk_ready.json'
            if ready.exists() and not disk_submitted:
                from amendment015.disk import disk_job
                gate=json.loads(ready.read_text())
                for p,h in gate['sources'].items():
                    if digest(ROOT/p)!=h:raise RuntimeError('DISK_SOURCE_CHANGED:'+p)
                item=next(x for x in config['sample'] if x['id']=='06')
                pending.append(dict(item,disk=True));needs['06']=gate['residual_ram_estimated_bytes']
                disk_submitted=True
            used=sum(needs[x['id']] for x in running.values())
            # One development/equivalence process reserves the eighth Python slot.
            limit=6 if ready.exists() else 5
            processes=[psutil.Process()]+psutil.Process().children(recursive=True)
            rss={str(p.pid):p.memory_info().rss for p in processes if p.is_running()}
            external=OUT/'disk_test_resources.json'
            external_rss=0
            if external.exists():
                record=json.loads(external.read_text())
                try:external_rss=psutil.Process(record['pid']).memory_info().rss
                except psutil.NoSuchProcess:pass
            if sum(rss.values())+external_rss>config['memory_budget_bytes']:
                raise MemoryError('AGGREGATE_RSS_EXCEEDS_FROZEN_ALLOCATION')
            for item in list(pending):
                need=needs[item['id']]
                if len(running)<limit and used+need+external_rss<=config['memory_budget_bytes']:
                    function=disk_job if item.get('disk') else exact_job
                    running[pool.submit(function,item)]=item;pending.remove(item);used+=need
            done,_=wait(running,timeout=5,return_when=FIRST_COMPLETED) if running else (set(),set())
            for future in done:
                item=running.pop(future);future.result();complete.append(item['id'])
            atomic(OUT/'reference_progress.json',dict(status='running',completed=sorted(complete),
                active=sorted(x['id'] for x in running.values()),pending=sorted(x['id'] for x in pending),
                disk_waiting=not disk_submitted,estimated_active_bytes=used,rss_by_pid=rss,
                aggregate_rss_bytes=sum(rss.values()),updated_utc=utcnow().isoformat()))
            if not running:time.sleep(1)
        pool.shutdown(wait=True)
        records=[]
        for item in config['sample']:
            path=OUT/'references'/f"{item['id']}_certificate.json";c=json.loads(path.read_text())
            if c['input_sha256']!=digest(OUT/'references'/f"{item['id']}_inputs.json") or c['status']!='complete':raise RuntimeError('CERTIFICATE_INCOMPATIBLE')
            records.append(dict(id=item['id'],certificate=path.name,sha256=digest(path),age=c['age'],infinite=c['infinite'],rate=c['rate'],subdivisions=4,input_sha256=c['input_sha256']))
        freeze(OUT/'references/manifest.json',dict(status='complete',N=9,seed=20261117015,
            configuration_sha256=digest(OUT/'configuration.json'),age_source_sha256=digest(ROOT/'analysis/amendment015/age.py'),references=records))
        from amendment015.age import require_manifest
        require_manifest(OUT/'references/manifest.json');ledger('references_frozen')
    except BaseException:
        pool.terminate_workers();raise

if __name__=='__main__':
    try:main()
    except Exception as error:
        import traceback
        stop_state(error);traceback.print_exc();raise SystemExit(1)
