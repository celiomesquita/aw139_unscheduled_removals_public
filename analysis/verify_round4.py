"""Run repository checks without the A5 refit forbidden in round 4."""
import json
import sys
import unittest
from pathlib import Path

from a15_stability import protected_hashes

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = 'test_pipeline.TestPipeline.test_complete_pipeline_twice_identical'


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    before = protected_hashes()
    tests = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / 'tests'))))
    excluded = [test.id() for test in tests if test.id() == EXCLUDED]
    if excluded != [EXCLUDED]:
        raise RuntimeError('Expected historical refit test was not identified')
    print('Excluded A5 refit explicitly forbidden by round 4: ' + EXCLUDED, flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(
        test for test in tests if test.id() != EXCLUDED))
    unchanged = before == protected_hashes()
    proof = dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                 excluded=excluded, reason='Author forbids reopening or refitting A5/A4',
                 protected_files_unchanged=unchanged)
    (ROOT / 'data/derived/a15/verification.json').write_text(
        json.dumps(proof, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == '__main__':
    sys.exit(main())
