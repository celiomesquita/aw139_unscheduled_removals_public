"""Verify two full generator runs and repository checks without refitting A5."""
import json
import subprocess
import sys
import unittest

from a16_generator import ROOT, OUT, committed_protocol, sha
from a15_stability import protected_hashes
from verify_round4 import EXCLUDED, flatten


def snapshot():
    return {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}


def main():
    revision, protocol_hash = committed_protocol()
    before = protected_hashes()
    first = snapshot()
    if 'manifest.json' not in first:
        raise RuntimeError('A first complete generator run is required')
    run = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'analysis/a16_generator.py'), '--validate'],
                         cwd=ROOT)
    if run.returncode not in (0, 2):
        raise RuntimeError('Generator replay execution failed')
    second = snapshot()
    if first != second:
        raise RuntimeError('Generator replay is not identical')
    suite = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / 'tests'))))
    if sum(t.id() == EXCLUDED for t in suite) != 1:
        raise RuntimeError('Expected A5 refit test was not identified')
    print('Excluded historical A5 refit: ' + EXCLUDED, flush=True)
    result = unittest.TextTestRunner().run(unittest.TestSuite(t for t in suite if t.id() != EXCLUDED))
    unchanged = before == protected_hashes() and committed_protocol() == (revision, protocol_hash)
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    proof = dict(full_generator_runs=2, identical_artifacts=len(first), sha256=second,
        protected_files_unchanged=unchanged, protocol_sha256=protocol_hash,
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        excluded=[EXCLUDED], gate_passed=manifest['gate_passed'],
        pilot_executed=False, power_executed=False, a9_executed=False)
    (ROOT / 'data/derived/a16/verification.json').write_text(
        json.dumps(proof, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == '__main__':
    sys.exit(main())
