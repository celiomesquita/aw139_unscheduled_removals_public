"""T13/T14: two full diagnostic replays, independence and pre-commit tests."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from a15_stability import protected_hashes
from a16_null_diagnosis import OUT, ROOT, sha
from verify_round4 import EXCLUDED, flatten


def preserved():
    values = protected_hashes()
    values.pop('paper/manuscript.tex')
    names = ['analysis/a5_report.md', 'analysis/a4_report.md', 'analysis/preregistro_A16_A9.md',
             'analysis/a5_models.py', 'analysis/a5_validation.py', 'analysis/a4_models.py',
             'analysis/a4_validation.py']
    paths = [ROOT / name for name in names]
    paths += list((ROOT / 'analysis').glob('emenda_A[45]_*.md'))
    paths += [ROOT / 'analysis' / f'emenda_A16_A9_{i:03d}.md' for i in range(1, 6)]
    values.update({p.relative_to(ROOT).as_posix(): sha(p) for p in paths})
    return values


def snapshot():
    values = {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}
    values['analysis/a16_null_diagnosis.md'] = sha(ROOT / 'analysis/a16_null_diagnosis.md')
    values['exposure_independence.json'] = sha(ROOT / 'data/derived/a16/exposure_independence.json')
    return values


def main():
    before = preserved()
    def replay():
        for script, arguments in (('a16_null_diagnosis.py', ['--workers', '6']),
                                  ('check_exposure_independence.py', [])):
            subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'analysis' / script), *arguments],
                           cwd=ROOT, check=True)
        return snapshot()
    first, second = replay(), replay()
    if first != second:
        raise RuntimeError('Round 5 diagnostic outputs are not identical')
    suite = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / 'tests'))))
    print('Excluded historical A5 refit: T15 is authorized only after amendment 006 commit.', flush=True)
    # The A15 replay test refreshes its manifest with the concurrent manuscript hash.
    # Preserve historical metadata as well as numerical artifacts in this round.
    a15_manifest = ROOT / 'data/derived/a15/manifest.json'
    historical_metadata = a15_manifest.read_bytes()
    try:
        result = unittest.TextTestRunner().run(unittest.TestSuite(t for t in suite if t.id() != EXCLUDED))
    finally:
        if a15_manifest.read_bytes() != historical_metadata:
            a15_manifest.write_bytes(historical_metadata)
    unchanged = before == preserved()
    proof = dict(full_diagnostic_runs=2, identical_artifacts=len(first), sha256=second,
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        excluded=[EXCLUDED], reason='T15 requires amendment 006 commit',
        original_artifacts_unchanged=unchanged, real_models_refitted=0,
        corrected_real_results_produced=False, flow17_executed=False,
        amendment_006_sha256=sha(ROOT / 'analysis/emenda_A16_A9_006.md'))
    (ROOT / 'data/derived/a16/round5_verification.json').write_text(
        json.dumps(proof, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
