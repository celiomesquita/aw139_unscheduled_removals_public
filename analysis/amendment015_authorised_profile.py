"""T20 timing entry point recognising the already audited reference exception."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import time
PROCESS_START = time.perf_counter()

import json
import traceback
from unittest.mock import patch

from amendment015.state import OUT, ROOT, atomic, digest, freeze, ledger, utcnow
from amendment015_authorised_verification import audited_sources


def run():
    import amendment015_profile as profile
    config = json.loads((OUT / 'configuration.json').read_text())
    audited_sources(config)
    verification = json.loads((OUT / 'verification_manifest.json').read_text())
    if (verification['status'] != 'passed' or verification['N'] != 9 or
            verification['reference_manifest_sha256'] != digest(OUT / 'references/manifest.json') or
            {r['id'] for r in verification['records']} != {f'{i:02d}' for i in range(9)} or
            not all(r['passed'] for r in verification['records'])):
        raise RuntimeError('FULL_VERIFICATION_NOT_PASSED')
    freeze(OUT / 'authorised_profile_configuration.json', dict(
        sources={str(p.relative_to(ROOT)): digest(p) for p in (
            ROOT / 'analysis/amendment015_authorised_profile.py',
            ROOT / 'analysis/amendment015_authorised_verification.py',
            ROOT / 'analysis/amendment015_profile.py')},
        reference_manifest_sha256=digest(OUT / 'references/manifest.json'),
        verification_manifest_sha256=digest(OUT / 'verification_manifest.json'),
        numeric_code_unchanged=True, audit_of_exception_already_approved=True,
        watchdog_seconds=10800, process_start_before_scientific_imports=True,
        cell=71, complete_policies=6, workers=6, executor_python_processes_max=8,
        native_threads=1, cbc_threads=1, effects_and_alarms_closed=True,
        technical_pilot_and_main_authorised=False))
    profile.PROCESS_START = PROCESS_START
    with patch.object(profile, 'check_sources', audited_sources):
        profile.run()


if __name__ == '__main__':
    try:
        run()
    except BaseException as error:
        failure = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc(), utc=utcnow().isoformat())
        atomic(OUT / 'authorised_profile_failure.json', failure)
        ledger('T20_STOP', stop=failure)
        traceback.print_exc()
        raise SystemExit(1)
