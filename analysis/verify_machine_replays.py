"""T17d isolated replays. Run only after the complete isolated suite passes.

ROOT must be an isolated checkout; REFERENCE is the preserved author checkout.
No fitting of A9 policies, gain inspection, R selection or historical writes.
"""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import time
import traceback

from machine_reproduction import (compare_old_csv_bytes, compare_old_json,
                                  old_digest_matches, compare_hierarchical_csv_bytes,
                                  compare_hierarchical_json)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_bytes(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.name.endswith('.gz') else data


def snapshot(folder):
    return {p.name: digest(p) for p in folder.iterdir() if p.is_file() and p.name != 'runtime.json'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--first-replica', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reference = args.reference.resolve()
    if root == reference or reference in root.parents:
        raise RuntimeError('Replay requires an isolated checkout')
    out = root / 'data/derived/machine_transfer/replays'
    out.mkdir(parents=True, exist_ok=True)
    proof = dict(status='running', historical_modified=False, outcomes_inspected=False)
    started = time.perf_counter()
    try:
        import a16_flow17 as flow
        config = json.loads((reference / 'data/derived/a16/flow17/configuration.json').read_text())
        cell = config['cells'][0]
        old = reference / 'data/derived/a16/flow17/replicas' / cell['id'] / '000'
        old_summary = json.loads((old / 'summary.json').read_text())
        # Verify frozen reference bytes before any numerical comparison.
        for name, expected in old_summary['artifacts'].items():
            if digest(old / name) != expected:
                raise AssertionError('Frozen replica artifact hash differs: ' + name)
        flow.initializer(False)
        first = out / 'flow17_run1'
        if args.first_replica is not None:
            shutil.copytree(args.first_replica, first)
            record = json.loads((first / 'summary.json').read_text())
            proof['first_replica_reused_from'] = str(args.first_replica)
        else:
            record, _ = flow.worker(cell, 0, first)
        if not all(v['status'] == 'ok' for v in record['variants'].values()):
            raise AssertionError('Flow17 execution failed')
        proof['flow17'] = dict(cell=cell['id'], replicate=0, included_in_R=False,
                               max_abs_differences={}, columns={}, same_host_bitwise=False)
        if record['artifacts'].keys() != old_summary['artifacts'].keys():
            raise AssertionError('Replica artifact set changed')
        for name in old_summary['artifacts']:
            columns = {}
            proof['flow17']['columns'][name] = columns
            difference = compare_hierarchical_csv_bytes(csv_bytes(first / name), csv_bytes(old / name), name, columns)
            proof['flow17']['max_abs_differences'][name] = difference
            (out / 'verification.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
        # Output hashes change with float rendering; validate their own bytes,
        # compare the science separately, and never exempt input hashes.
        for name, expected in record['artifacts'].items():
            if digest(first / name) != expected:
                raise AssertionError('New replica output hash differs')
        a = {k: v for k, v in record.items() if k != 'artifacts'}
        b = {k: v for k, v in old_summary.items() if k != 'artifacts'}
        proof['flow17']['summary_columns'] = {}
        proof['flow17']['summary_max_abs_difference'] = compare_hierarchical_json(
            a, b, proof['flow17']['summary_columns'])
        second = out / 'flow17_run2'
        flow.worker(cell, 0, second)
        if snapshot(first) != snapshot(second):
            raise AssertionError('Local flow17 runs are not bitwise identical')
        proof['flow17']['same_host_bitwise'] = True
        proof['flow17']['linux_reference_sha256'] = snapshot(first)
        (out / 'verification.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')

        import decompose_pilot_a9 as decomposition
        old_out = reference / 'data/derived/a9/decomposition'
        new_out = root / 'data/derived/a9/decomposition'
        old_proof = json.loads((old_out / 'verification.json').read_text())
        names = list(old_proof['sha256'])
        old_metadata = json.loads((old_out / 'decomposition.json').read_text())
        old_ledger = json.loads((old_out / 'accumulated_costs.json').read_text())
        for name, expected in old_metadata['sources'].items():
            if not old_digest_matches((root / name).read_bytes(), expected):
                raise AssertionError('Decomposition input hash differs: ' + name)
        prior_name = old_ledger['prior_ledger']
        if not old_digest_matches((root / prior_name).read_bytes(), old_ledger['prior_ledger_sha256']):
            raise AssertionError('Prior ledger input hash differs')
        decomposition.run()
        proof['decomposition'] = dict(max_abs_differences={}, columns={}, same_host_bitwise=False,
            source_hashes_exact_or_documented_CRLF=True)
        for name in names:
            old_path, new_path = old_out / name, new_out / name
            if not old_digest_matches(old_path.read_bytes(), old_proof['sha256'][name]):
                raise AssertionError('Decomposition reference hash differs: ' + name)
            columns = {}
            proof['decomposition']['columns'][name] = columns
            if name.endswith('.csv'):
                difference = compare_old_csv_bytes(new_path.read_bytes(), old_path.read_bytes(), columns)
            else:
                a, b = json.loads(new_path.read_text()), json.loads(old_path.read_text())
                if name == 'decomposition.json':
                    for source, value in a['sources'].items():
                        if digest(root / source) != value:
                            raise AssertionError('New decomposition source hash differs')
                    del a['sources'], b['sources']
                if name == 'accumulated_costs.json':
                    if a['prior_ledger_sha256'] != digest(root / prior_name):
                        raise AssertionError('New prior ledger digest differs')
                    del a['prior_ledger_sha256'], b['prior_ledger_sha256']
                    for new_event, old_event in zip(a['additional_events'], b['additional_events']):
                        source = old_event['source']
                        if (not old_digest_matches((root / source).read_bytes(), old_event['sha256'])
                                or digest(root / source) != new_event['sha256']):
                            raise AssertionError('Decomposition event input hash differs')
                        del new_event['sha256'], old_event['sha256']
                difference = compare_old_json(a, b, columns)
            proof['decomposition']['max_abs_differences'][name] = difference
        local = {name: digest(new_out / name) for name in names}
        report = root / 'analysis/a9_partial_time_decomposition.md'
        local['report'] = digest(report)
        decomposition.run()
        repeated = {name: digest(new_out / name) for name in names}
        repeated['report'] = digest(report)
        if local != repeated:
            raise AssertionError('Local decompositions are not bitwise identical')
        proof['decomposition']['same_host_bitwise'] = True
        proof['status'] = 'passed'
    except Exception as error:
        proof.update(status='STOP', error_type=type(error).__name__, error=str(error))
        traceback.print_exc()
    finally:
        proof['validation_wall_seconds'] = time.perf_counter() - started
        (out / 'verification.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    return 0 if proof['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
