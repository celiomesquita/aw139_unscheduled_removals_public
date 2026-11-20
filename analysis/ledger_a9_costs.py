"""Freeze recorded earlier A9 costs without duplicating copied verification proofs."""
import json

from a16_generator import ROOT, sha
from round5_execution import atomic_json


def main():
    specs = [
        ('data/derived/a9/pilot/authorised_interruption.json', 'wall_seconds_since_pilot_started'),
        ('data/derived/a9/numerical_validation/verification.json', 'test_seconds'),
        ('data/derived/a9/warmup_verification.json', 'test_seconds'),
        ('data/derived/a9/integration_before_zero_exposure_fix.json', 'test_seconds'),
        ('data/derived/a9/optimisation/baseline/integration_verification.json', 'test_seconds'),
        ('data/derived/a9/optimisation/verification.json', 'verification_wall_seconds'),
        ('data/derived/a9/optimisation/kernel_benchmark_rank_update_only.json', 'whole_benchmark_wall_seconds'),
        ('data/derived/a9/optimisation/kernel_benchmark_direct_integral.json', 'whole_benchmark_wall_seconds'),
        ('data/derived/a9/optimisation/kernel_benchmark.json', 'whole_benchmark_wall_seconds')]
    events, seen = [], set()
    for name, key in specs:
        path = ROOT / name
        digest = sha(path)
        if digest in seen:
            continue
        seen.add(digest)
        data = json.loads(path.read_text())
        events.append(dict(source=name, sha256=digest, field=key, seconds=data[key]))
    # This exact test duration was recorded in the original A9 audit; surrounding
    # unmeasured preparation is listed as a gap rather than imputed.
    events.append(dict(source='registro_auditoria.md section 23', field='reported_test_duration',
                       seconds=271.272, scope='reported test execution only'))
    payload = dict(events=events, known_recorded_seconds=sum(row['seconds'] for row in events),
        budget_hours_total=120, unknown_costs_not_imputed=True,
        gaps=['earlier unrecorded targeted tests, unsuccessful verification and preparation overhead'],
        excludes_duplicate_integration_proof=True,
        excludes_integration_test_time_already_in_optimisation_verification=True)
    output = ROOT / 'data/derived/a9/optimisation/prior_costs.json'
    if output.exists() and json.loads(output.read_text()) != payload:
        raise RuntimeError('Frozen earlier-cost ledger differs; preserve and version it')
    atomic_json(output, payload)
    print(payload['known_recorded_seconds'])


if __name__ == '__main__':
    main()
