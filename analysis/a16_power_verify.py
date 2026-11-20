"""Two complete synthetic replays and checks before starting the long A16 job."""
import json
import time
import unittest

from a16_power import OUT, ROOT, cells, execute_replica, freeze_config, sha
from a16_generator import load_design
from a15_stability import protected_hashes
from verify_round4 import EXCLUDED, flatten


def snapshot(folder):
    return {p.name: sha(p) for p in sorted(folder.iterdir()) if p.is_file()}


def main():
    config = freeze_config()
    before = protected_hashes()
    truth, _, _, channels, _, _ = load_design()
    cell = cells()[0]
    first = OUT / 'replicas' / cell['id'] / '000'
    second = OUT / 'reproducibility' / (cell['id'] + '_000')
    if (first / 'summary.json').exists():
        reference = json.loads((first / 'summary.json').read_text(encoding='utf-8'))
    else:
        reference = execute_replica(cell, 0, truth, channels, first)
    if not all(v['status'] == 'ok' for v in reference['variants'].values()):
        raise RuntimeError('The first complete synthetic replica did not execute successfully')
    started = time.perf_counter()
    repeated = execute_replica(cell, 0, truth, channels, second)
    if snapshot(first) != snapshot(second) or reference != repeated:
        raise RuntimeError('Two complete synthetic A16 replays differ')
    suite = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / 'tests'))))
    if sum(t.id() == EXCLUDED for t in suite) != 1:
        raise RuntimeError('Historical A5 refit exclusion is not unique')
    print('Excluded historical A5 refit:', EXCLUDED, flush=True)
    result = unittest.TextTestRunner().run(unittest.TestSuite(t for t in suite if t.id() != EXCLUDED))
    proof = dict(configuration_sha256=config['configuration_sha256'], complete_synthetic_replays=2,
        cell=cell['id'], replicate=0, repeated_replica_not_counted_as_new=True,
        identical_artifacts=len(snapshot(first)), sha256=snapshot(first), tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), excluded=[EXCLUDED],
        protected_files_unchanged=before == protected_hashes(), replay_and_test_seconds=time.perf_counter() - started)
    (OUT / 'verification.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() and proof['protected_files_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
