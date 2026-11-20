"""Verify A9 preparation twice and run the full suite preserving replay metadata."""
import json
import unittest

import mip

from a16_generator import ROOT, sha
from a9_resources import OUT, run
from round5_execution import atomic_json, check_historical


def main():
    configuration = json.loads((ROOT / 'data/derived/a16/flow17/configuration.json').read_text())
    expected = configuration['historical']
    first = run()
    second = run()
    if first != second:
        raise RuntimeError('A9 resource preparation is not reproducible')
    paths = [ROOT / 'data/derived' / p for p in
             ('a15/manifest.json', 'pipeline_manifest.json', 'pipeline_verification.json')]
    metadata = {p: p.read_bytes() for p in paths if p.exists()}
    try:
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    finally:
        for path, original in metadata.items():
            if path.read_bytes() != original:
                path.write_bytes(original)
    check_historical(expected)
    atomic_json(ROOT / 'data/derived/a9/startup_verification.json',
                dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                     repeated_resource_preparation_identical=True, mip_version=mip.__version__,
                     historical_artifacts_unchanged=True, replay_metadata_restored=True,
                     pilot_started=False, simulated_policy_replicas=0,
                     resource_manifest_sha256=sha(OUT / 'manifest.json')))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
