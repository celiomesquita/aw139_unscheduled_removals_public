"""Storage equivalence on two unaltered aircraft calendars from the frozen sample."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import json
import math
from pathlib import Path
import shutil
import struct
import time
import traceback
import psutil
from amendment015.state import OUT,ROOT,atomic,digest,freeze,check_deadline,utcnow
from amendment015.disk import disk_threshold,resource_estimate,SCRATCH
from a9_static_fast import exhaustive_threshold


def main():
    config=json.loads((OUT/'configuration.json').read_text())
    check_deadline(references=True,refresh=False)
    SCRATCH.mkdir(parents=True,exist_ok=True)
    atomic(OUT/'disk_test_resources.json',dict(pid=os.getpid(),reserved_bytes=1024**3,started_utc=utcnow().isoformat()))
    results=[]
    for sample_id in ('02','05'):
        item=next(x for x in config['sample'] if x['id']==sample_id)
        eligible=[(i,c) for i,c in enumerate(item['contexts']) if c['visits'] and sum(c['daily'])>0]
        index,context=min(eligible,key=lambda x:(len(set(x[1]['visits'])),x[0]))
        model=item['model'];arguments=([context],model['beta'],model['eta'],model['nu'],item['r'],4)
        atomic(OUT/'disk_equivalence_progress.json',dict(sample=sample_id,aircraft_context_index=index,
            stage='RAM',updated_utc=utcnow().isoformat()))
        before=time.perf_counter();ram=exhaustive_threshold(*arguments);ram_wall=time.perf_counter()-before
        check_deadline(references=True,refresh=False)
        atomic(OUT/'disk_equivalence_progress.json',dict(sample=sample_id,aircraft_context_index=index,
            stage='memmap',updated_utc=utcnow().isoformat()))
        before=time.perf_counter();disk=disk_threshold(*arguments);disk_wall=time.perf_counter()-before
        check_deadline(references=True,refresh=False)
        def scientific_bytes(result):
            return struct.pack('<d',result[0])+json.dumps(result[1],sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        rb,db=scientific_bytes(ram),scientific_bytes(disk)
        import hashlib
        result=dict(sample_id=sample_id,pn=item['pn'],r=item['r'],aircraft_context_index=index,
            test_scope='one complete unmodified aircraft calendar from the frozen composite; not a replacement or subsample for any of the nine reference certificates',
            input_sha256=digest(OUT/'references'/f'{sample_id}_inputs.json'),
            context=context,beta=model['beta'],eta=model['eta'],nu=model['nu'],subdivisions=4,
            age_bytes_equal=struct.pack('<d',ram[0])==struct.pack('<d',disk[0]),
            rate_bytes_equal=struct.pack('<d',ram[1]['expected_rate_variable_groups'])==struct.pack('<d',disk[1]['expected_rate_variable_groups']),
            diagnostics_bytes_equal=json.dumps(ram[1],sort_keys=True).encode()==json.dumps(disk[1],sort_keys=True).encode(),
            scientific_bytes_equal=rb==db,ram_sha256=hashlib.sha256(rb).hexdigest(),disk_sha256=hashlib.sha256(db).hexdigest(),
            ram_age=None if math.isinf(ram[0]) else ram[0],ram_infinite=math.isinf(ram[0]),ram_diagnostics=ram[1],
            disk_age=None if math.isinf(disk[0]) else disk[0],disk_infinite=math.isinf(disk[0]),disk_diagnostics=disk[1],
            ram_wall_seconds=ram_wall,disk_wall_seconds=disk_wall)
        results.append(result)
        atomic(OUT/'disk_equivalence_partial.json',dict(tests=results,complete=False))
        if rb!=db:raise ArithmeticError('RAM_MEMMAP_NOT_BYTE_IDENTICAL:'+sample_id)
    sources={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'analysis/amendment015/disk.py',Path(__file__),ROOT/'analysis/amendment015/resume.py',ROOT/'analysis/amendment015_resume.py']}
    freeze(OUT/'disk_equivalence.json',dict(status='passed',tests=results,sources=sources,
        configuration_sha256=digest(OUT/'configuration.json'),completed_utc=utcnow().isoformat()))
    item=next(x for x in config['sample'] if x['id']=='06')
    estimate=resource_estimate(item);free=shutil.disk_usage(SCRATCH).free
    estimate.update(id='06',allocation_bytes=config['memory_budget_bytes'],disk_free_bytes=free,
        disk_safety_reserve_bytes=2*1024**3,updated_utc=utcnow().isoformat(),
        fits_ram=estimate['residual_ram_estimated_bytes']<=config['memory_budget_bytes'],
        fits_disk=estimate['disk_estimated_bytes']+2*1024**3<=free)
    atomic(OUT/'disk_resource_preflight.json',estimate)
    if not estimate['fits_ram'] or not estimate['fits_disk']:raise MemoryError('DISK_REFERENCE_RESIDUAL_RAM_OR_DISK_DOES_NOT_FIT')
    # Readiness is published only after both exact comparisons and capacity checks.
    freeze(OUT/'disk_ready.json',dict(**estimate,sources=sources,equivalence_sha256=digest(OUT/'disk_equivalence.json')))
    atomic(OUT/'disk_equivalence_progress.json',dict(stage='passed_and_ready',updated_utc=utcnow().isoformat()))

if __name__=='__main__':
    try:main()
    except Exception as error:
        atomic(OUT/'disk_failure.json',dict(type=type(error).__name__,message=str(error),utc=utcnow().isoformat()))
        traceback.print_exc();raise SystemExit(1)
