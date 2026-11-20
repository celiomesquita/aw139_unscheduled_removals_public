"""Read-only scientific checks and documentary closeout of the budget stop."""
import json
import math
import unittest

import pandas as pd

from a15_stability import protected_hashes
from a16_generator import ROOT, OUT, committed_protocol, sha


def main():
    verification = json.loads((ROOT / 'data/derived/a16/verification.json').read_text(encoding='utf-8'))
    generator = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    pilot = json.loads((ROOT / 'data/derived/a16/pilot_manifest.json').read_text(encoding='utf-8'))
    timing = pd.read_csv(ROOT / 'data/derived/a16/pilot_timing.csv', float_precision='round_trip')
    for name, digest in verification['sha256'].items():
        if sha(OUT / name) != digest:
            raise RuntimeError('Generator artifact changed: ' + name)
    for name, digest in generator['inputs'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Generator input changed: ' + name)
    protected = protected_hashes()
    revision, protocol_hash = committed_protocol()
    protected['analysis/preregistro_A16_A9.md'] = protocol_hash
    if protected != generator['protected']:
        raise RuntimeError('Protected artifacts changed')
    if len(timing) != 5 or pilot['pilot_in_results'] or pilot['effects_inspected']:
        raise RuntimeError('Invalid timing-only pilot')
    raw_r = 50 * math.floor(48 * 3600 / (9 * 1.5 * timing.seconds.max()) / 50)
    if raw_r != pilot['raw_R'] or pilot['budget_passed'] or raw_r >= 200:
        raise RuntimeError('Budget-stop arithmetic does not match recorded pilot')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='*documents.py')
    result = unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():
        return 1
    files = ['analysis/a16_generator.py', 'analysis/a16_verify.py', 'analysis/a16_pilot.py',
             'analysis/a16_report.py', 'analysis/a16_closeout.py', 'analysis/emenda_A16_A9_001.md',
             'analysis/emenda_A16_A9_002.md', 'requirements.txt', '.gitignore',
             'analysis/a16_report.md', 'plano_executivo_de_melhorias.md', 'registro_auditoria.md']
    state = dict(status='stopped_budget', protocol_revision=revision, protocol_sha256=protocol_hash,
        generator_gate_passed=True, generator_full_runs=2, identical_generator_artifacts=12,
        numerical_and_repository_tests=verification['tests_run'], final_document_tests=result.testsRun,
        protected_files_unchanged=True, pilot_replicates=5, budget_A16_hours=48, raw_R=raw_r,
        minimum_R=200, required_A16_hours=9 * 1.5 * 200 * timing.seconds.max() / 3600,
        power_executed=False, type_I_estimated=False, a7_executed=False, a9_executed=False,
        a10_executed=False, excluded_tests=verification['excluded'],
        provenance={name: sha(ROOT / name) for name in files},
        pilot_manifest_sha256=sha(ROOT / 'data/derived/a16/pilot_manifest.json'))
    (ROOT / 'data/derived/a16/execution.json').write_text(
        json.dumps(state, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('T12 stopped by preregistered budget rule; protected hashes unchanged.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
