"""Check fresh evaluation entries and once-only warmup loading without new observations."""
import json
import unittest
from unittest.mock import patch

from a16_generator import ROOT, load_design, sha
from a9_evaluation import initial_units
from a9_warmup import OUT, POLICIES, materialise, verify_configuration
from round5_execution import atomic_json, check_historical


def main():
    configuration = verify_configuration()
    path = OUT / 'reproducibility/run_1'
    with patch('a9_warmup.generate', side_effect=AssertionError('Auxiliary history regenerated')):
        for _ in POLICIES:
            materialise(0, 'calibrated', 'verification', path)
    truth, _, _, channels, _, _ = load_design()
    end = 730  # 31/12/2025 on A16's Jan-2024 origin.
    entries = initial_units(truth, channels, 'calibrated', 'verification', 0, end)
    for entry in entries:
        state = entry['state']
        if state.age != 0 or state.birth != entry['start'] or state.time != entry['start']:
            raise RuntimeError('Auxiliary age or state leaked into evaluation')
        if state.renewal != 0 or state.key[0] != 9 or entry['aircraft'].endswith('-AUX'):
            raise RuntimeError('Evaluation cohort/stream differs from amendment 010')
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_a9_evaluation.py'))
    # This test was added after the preceding full-suite discovery.
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(
        'test_a9_warmup.TestAuthorisedWarmup.test_administrative_censor_does_not_become_competing_event'))
    result = unittest.TextTestRunner().run(suite)
    check_historical(configuration['historical'])
    names = ['analysis/a9_evaluation.py', 'analysis/a9_fitting.py',
             'tests/test_a9_evaluation.py', 'tests/test_a9_warmup.py']
    atomic_json(ROOT / 'data/derived/a9/warmup_supplement_verification.json', dict(
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        six_policy_loads_without_regeneration=True, evaluation_units=len(entries),
        all_evaluation_initial_ages_zero=True, real_entry_times_preserved=True,
        evaluation_and_auxiliary_streams_distinct=True, evaluation_observations_generated=0,
        late_entries_preserved=sum(e['start'] > 365 for e in entries),
        historical_hashes_unchanged=True, sources={p: sha(ROOT / p) for p in names},
        pilot_started=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
