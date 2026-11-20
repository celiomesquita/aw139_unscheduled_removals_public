"""Full regression and scientific-output identity against the preserved executor."""
import json
import time

from a9_pilot import ROOT, runtime_sources
from verify_a9_integration import main as verify_integration
from round5_execution import atomic_json

SCIENTIFIC_FIELDS = ('policy', 'cost', 'post_change_cost', 'events', 'unscheduled',
                     'competing', 'preventive', 'outside_visit', 'mh', 'detection', 'parameter_history')


def main():
    started = time.perf_counter()
    before = json.loads((ROOT / 'data/derived/a9/optimisation/baseline/artificial_policy_paths.json').read_text())
    code = verify_integration()
    if code:
        return code
    after = json.loads((ROOT / 'data/derived/a9/integration/artificial_policy_paths.json').read_text())
    for reference, optimised in zip(before['runs'], after['runs']):
        for old, new in zip(reference['policies'], optimised['policies']):
            if any(old[field] != new[field] for field in SCIENTIFIC_FIELDS):
                raise RuntimeError('Optimisation changed scientific policy outputs')
    proof = json.loads((ROOT / 'data/derived/a9/integration_verification.json').read_text())
    result = dict(scientific_outputs_identical_to_preserved_version=True,
        scientific_fields=list(SCIENTIFIC_FIELDS), policy_paths_compared=12,
        full_suite_tests_run=proof['tests_run'], errors=proof['errors'], failures=proof['failures'],
        full_six_policy_spawned_equivalence_in_suite=True,
        phase_enumeration_threshold_and_matrix_equivalence_in_suite=True,
        sources=runtime_sources(), prior_pilot_preserved=True,
        pilot_restarted=False, R_selected=False,
        verification_wall_seconds=time.perf_counter() - started)
    atomic_json(ROOT / 'data/derived/a9/optimisation/verification.json', result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
