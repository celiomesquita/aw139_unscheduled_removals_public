"""Run the full authorized T15 suite and preserve historical replay metadata."""
import json
import unittest

from a16_generator import ROOT
from round5_execution import atomic_json, check_historical, historical_hashes


def main():
    before = historical_hashes()
    paths = [ROOT / 'data/derived' / name for name in
             ('a15/manifest.json', 'pipeline_manifest.json', 'pipeline_verification.json')]
    metadata = {path: path.read_bytes() for path in paths if path.exists()}
    try:
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    finally:
        for path, payload in metadata.items():
            if path.read_bytes() != payload:
                path.write_bytes(payload)
    check_historical(before)
    atomic_json(ROOT / 'data/derived/errata_startup_verification.json',
        dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
             historical_A5_replay_authorized_and_included=True, historical_artifacts_unchanged=True,
             replay_metadata_restored=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
