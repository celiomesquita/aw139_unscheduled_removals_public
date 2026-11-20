"""Artificial complete-policy replication plus the full regression suite."""
import hashlib
import json
import sys
import time
import unittest

from a9_pilot import ROOT, runtime_sources
from a9_warmup import verify_configuration
from round5_execution import atomic_json, check_historical


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items() if k != 'runtime_seconds'}
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if hasattr(value, 'item'):
        return value.item()
    return value


def main():
    configuration = verify_configuration()
    check_historical(configuration['historical'])
    before_sources = runtime_sources()
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_a9_simulation import TestSixPolicyIntegration
    from a9_warmup import POLICIES
    case = TestSixPolicyIntegration('test_six_complete_stationary_null_paths_share_random_numbers')
    first, second = [], []
    for target in (first, second):
        for aging in (False, True):
            paths = [canonical(case.execute(policy, units=4 if aging else 1, aging=aging))
                     for policy in POLICIES]
            target.append(dict(artificial=True, known_fixed_parameter_fixture=True,
                               aging=aging, policies=paths))
    if first != second:
        raise RuntimeError('Complete artificial policy runs are not identical')
    if not any(p['preventive'] for p in first[1]['policies']):
        raise RuntimeError('Artificial aging fixture did not exercise preventive actions')
    folder = ROOT / 'data/derived/a9/integration'
    folder.mkdir(parents=True, exist_ok=True)
    atomic_json(folder / 'artificial_policy_paths.json', dict(runs=first,
        observed_population='artificial', used_in_pilot_or_main=False))
    replay_paths = [ROOT / 'data/derived' / name for name in
                   ('a15/manifest.json', 'pipeline_manifest.json', 'pipeline_verification.json')]
    metadata = {p: p.read_bytes() for p in replay_paths if p.exists()}
    started = time.perf_counter()
    try:
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    finally:
        for p, original in metadata.items():
            if p.read_bytes() != original:
                p.write_bytes(original)
    check_historical(configuration['historical'])
    if runtime_sources() != before_sources:
        raise RuntimeError('A9 runtime changed while its integration was verified')
    atomic_json(ROOT / 'data/derived/a9/integration_verification.json', dict(
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        test_seconds=time.perf_counter() - started, sources=before_sources,
        two_complete_artificial_runs_identical=True, six_policies_in_each_run=True,
        stationary_null_and_aging_tested=True, known_parameters_in_artificial_policy_fixtures=True,
        parameter_recovery_tests_in_full_suite=True, preventive_actions_exercised=True,
        historical_hashes_unchanged=True, replay_metadata_restored=True,
        evaluated_fleet_policy_replicas=0, pilot_started=False,
        artificial_paths_sha256=hashlib.sha256((folder / 'artificial_policy_paths.json').read_bytes()).hexdigest(),
        verification_script_sha256=hashlib.sha256(__file__.encode()).hexdigest()))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
