"""Run only the nine-case calibration verification after complete references."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import json
import traceback
from datetime import datetime,timezone
from amendment015.state import OUT,atomic,ledger,utcnow
from amendment015.verification import run

if __name__=='__main__':
    try:
        # Use the actual reference-freeze event, not the later launch time here.
        value=ledger()
        event=next((e for e in reversed(value['stage_events']) if e['stage']=='references_frozen'),None)
        if event is None:raise RuntimeError('REFERENCE_FREEZE_EVENT_ABSENT')
        finished=datetime.fromisoformat(event['started_utc'])
        deadline=min(datetime.fromisoformat(value['reference_deadline_utc']),
            datetime(2026,11,19,16,16,40,tzinfo=timezone.utc))
        if finished>deadline:raise TimeoutError('REFERENCE_MANIFEST_FROZEN_AFTER_ORIGINAL_24H_DEADLINE')
        value['reference_block_finished_utc']=finished.isoformat()
        value['reference_block_wall_seconds']=(finished-datetime.fromisoformat(value['reference_preparation_start_utc'])).total_seconds()
        atomic(OUT/'time_ledger.json',value)
        run()
        atomic(OUT/'state.json',dict(status='calibration_verified',references_complete=9,
            calibration_verification_passed=True,cheap_thresholds_computed=True,
            profiling_executed=False,main_executed=False,utc=utcnow().isoformat()))
    except Exception as error:
        value=ledger('technical_stop',stop=dict(code=type(error).__name__,message=str(error)))
        existing=OUT/'verification.json'
        partial=json.loads(existing.read_text()) if existing.exists() else None
        atomic(OUT/'verification_failure.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        atomic(OUT/'state.json',dict(status='STOP',stage='calibration_verification',
            error_type=type(error).__name__,error_code=str(error),references_complete=9,
            verification_executed=partial is not None,partial_verification=partial,
            calibration_verification_passed=False,profiling_executed=False,main_executed=False,
            consumption_seconds=value['consumed_seconds'],remaining_seconds=value['remaining_seconds']))
        traceback.print_exc();raise SystemExit(1)
