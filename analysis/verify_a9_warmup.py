"""Verify amendment 010 in isolated verification streams, without running a pilot."""
import hashlib
import json
import time
import unittest

import pandas as pd

from a16_generator import ROOT, sha
from a5_models import training_view
from a9_fitting import PolicyEvaluation, fit_observable
from a9_warmup import (OUT, POLICIES, SharedWarmup, evaluation_only,
                       initialise_configuration, materialise)
from round5_execution import atomic_json, check_historical


def main():
    configuration = initialise_configuration()
    first = materialise(0, 'calibrated', 'verification', OUT / 'reproducibility/run_1')
    second = materialise(0, 'calibrated', 'verification', OUT / 'reproducibility/run_2')
    names = ('generation_started.json', 'spells.csv', 'flights.csv', 'manifest.json')
    if any(sha(first / name) != sha(second / name) for name in names):
        raise RuntimeError('Full auxiliary generations are not identical')
    shared = SharedWarmup(first)
    baseline, clocks = shared.for_policy('P0')
    for policy in POLICIES:
        actual, actual_clocks = shared.for_policy(policy)
        pd.testing.assert_frame_equal(baseline, actual)
        pd.testing.assert_frame_equal(clocks, actual_clocks)
    if not evaluation_only(baseline).empty or baseline.preventive.any():
        raise RuntimeError('Auxiliary observation entered evaluation or preventive policy')
    engine = object.__new__(PolicyEvaluation)
    engine.spells = baseline
    views = {}
    for date in ('2024-01-01', '2024-02-01', '2025-02-01', '2025-12-01'):
        origin = pd.Timestamp(date)
        frame = training_view(engine.cohort(origin, 'principal'), origin)
        if frame.end.ge(origin).any():
            raise RuntimeError('Future auxiliary information in training')
        views[date] = frame
    pd.testing.assert_series_equal(views['2024-02-01'].end, views['2025-12-01'].end)
    if set(views['2024-02-01'].spell_id) != set(views['2025-12-01'].spell_id):
        raise RuntimeError('Auxiliary history disappeared after drift')
    domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
    # Closed auxiliary histories must yield identical fits at these later origins.
    fitted, meta_first = fit_observable(baseline, clocks, domain, pd.Timestamp('2024-02-01'))
    repeated, meta_later = fit_observable(baseline, clocks, domain, pd.Timestamp('2025-12-01'))
    if fitted != repeated:
        raise RuntimeError('Completed auxiliary history accumulated exposure at a later origin')
    metadata = json.loads((first / 'manifest.json').read_text())
    manifest = dict(configuration_sha256=configuration['configuration_sha256'],
        amendment010_sha256=sha(ROOT / 'analysis/emenda_A16_A9_010.md'),
        two_complete_generations_identical=True, identical_artifacts=len(names),
        all_six_policies_receive_identical_history=True,
        future_information_excluded=True, auxiliary_censor_dates_fixed=True,
        retained_after_drift=True, closed_history_fits_identical_across_origins=True,
        closed_history_parameter_sha256=hashlib.sha256(json.dumps(fitted, sort_keys=True).encode()).hexdigest(),
        training_spells_by_origin={date: len(frame) for date, frame in views.items()},
        historical_hashes_unchanged=True, verification_only=True,
        pilot_started=False, evaluation_policy_replicas=0,
        auxiliary_spells=metadata['spells'], auxiliary_events=metadata['events'],
        auxiliary_channels=metadata['auxiliary_channels'],
        unavailable_first_year_channels=metadata['unavailable_first_year_channels'])
    output = ROOT / 'data/derived/a9/warmup_verification.json'
    atomic_json(output, manifest)
    paths = [ROOT / 'data/derived' / name for name in
             ('a15/manifest.json', 'pipeline_manifest.json', 'pipeline_verification.json')]
    before = {p: p.read_bytes() for p in paths if p.exists()}
    started = time.perf_counter()
    try:
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    finally:
        for p, content in before.items():
            if p.read_bytes() != content:
                p.write_bytes(content)
    check_historical(configuration['historical'])
    manifest.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                    test_seconds=time.perf_counter() - started, replay_metadata_restored=True)
    atomic_json(output, manifest)
    print('Amendment 010 verified; no pilot or evaluation-policy replicate generated', flush=True)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
