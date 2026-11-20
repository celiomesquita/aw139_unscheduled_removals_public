"""Verification after author audit of the nine references and appended addendum.

The original 24 h attempt remains closed.  This entry point only recognises
the approved exception; it does not change calibration, Q, g or tolerances.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

import json
import traceback
from unittest.mock import patch

from amendment015.state import OUT, ROOT, atomic, check_deadline, digest, freeze, ledger, utcnow
from amendment015.age import require_manifest
from amendment015_extra06 import integrity


def audited_sources(config):
    value = json.loads((OUT / 'time_ledger.json').read_text())
    if value['additional06']['status'] != 'certified_stop_for_audit':
        raise RuntimeError('AUDITED_ADDITIONAL_REFERENCE_NOT_CERTIFIED')
    integrity(config, value['additional06'])
    for snapshot in ('implementation_sources.json', 'prospective_next_stage_sources_v2.json'):
        content = json.loads((OUT / snapshot).read_text())
        for name, expected in content.get('sources', content).items():
            if digest(ROOT / name) != expected:
                raise RuntimeError('AUDITED_PROSPECTIVE_SOURCE_CHANGED:' + name)
    require_manifest(OUT / 'references/manifest.json')


def run():
    from amendment015 import verification
    config = json.loads((OUT / 'configuration.json').read_text())
    check_deadline()
    audited_sources(config)
    if (OUT / 'verification.json').exists():
        raise RuntimeError('PRESERVED_VERIFICATION_REQUIRES_AUTHOR_REVIEW')
    freeze(OUT / 'authorised_verification_configuration.json', dict(
        author_decision='Audit of nine references, manifest and addendum approved; proceed to g and, only on pass, T20',
        original_reference_window_preserved=True,
        additional06_summary_sha256=digest(OUT / 'additional06/final_summary.json'),
        reference_manifest_sha256=digest(OUT / 'references/manifest.json'),
        numeric_configuration_sha256=digest(OUT / 'configuration.json'),
        original_amendment_prefix_sha256=json.loads((OUT / 'time_ledger.json').read_text())['additional06']['original_amendment_prefix_sha256'],
        sources={str(p.relative_to(ROOT)): digest(p) for p in (
            ROOT / 'analysis/amendment015_authorised_verification.py',
            ROOT / 'analysis/amendment015/verification.py',
            ROOT / 'analysis/amendment015_extra06.py')},
        g_max=0.005, g_negative_stop=-1e-8, sample_size=9,
        numerical_code_unchanged=True, effects_and_alarms_closed=True))
    value = ledger('calibration_verification_authorised_after_audit')
    value['verification_authorisation'] = dict(
        recorded_utc=utcnow().isoformat(),
        configuration_sha256=digest(OUT / 'authorised_verification_configuration.json'),
        additional_reference_audit_approved=True,
        reference_manifest_sha256=digest(OUT / 'references/manifest.json'),
        no_intermediate_audit_stop_required=True)
    atomic(OUT / 'time_ledger.json', value)
    with patch.object(verification, 'check_sources', audited_sources):
        records = verification.run()
    audited_sources(config)
    atomic(OUT / 'state.json', dict(status='calibration_verified', references_complete=9,
        calibration_verification_passed=True, cheap_thresholds_computed=True,
        profiling_executed=False, main_executed=False, utc=utcnow().isoformat()))
    print(json.dumps(dict(status='passed', contexts=len(records))))


if __name__ == '__main__':
    try:
        run()
    except BaseException as error:
        failure = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc(), utc=utcnow().isoformat())
        value = ledger('calibration_verification_STOP', stop=failure)
        atomic(OUT / 'verification_failure.json', failure)
        atomic(OUT / 'state.json', dict(status='STOP', stage='calibration_verification',
            calibration_verification_passed=False, profiling_executed=False,
            main_executed=False, failure=failure,
            global_consumed_seconds=value['consumed_seconds'], global_remaining_seconds=value['remaining_seconds']))
        traceback.print_exc()
        raise SystemExit(1)
