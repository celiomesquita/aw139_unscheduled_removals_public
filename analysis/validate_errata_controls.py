"""T15 exact realized-exposure controls: forecasts, metrics, calibration and bootstrap."""
import pandas as pd

from a16_generator import ROOT, sha
from errata_exposicao import output_folder
from round5_execution import atomic_json


def assert_same(original, corrected, keys):
    extra = set(original.columns) - set(corrected.columns)
    if extra:
        raise RuntimeError('Missing original columns: ' + ', '.join(sorted(extra)))
    left = original.sort_values(keys, kind='stable').reset_index(drop=True)
    right = corrected[original.columns].sort_values(keys, kind='stable').reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right, check_exact=True)


def main():
    rows = []
    for model in ('A5', 'A4'):
        original = ROOT / 'data/derived' / model.lower()
        for threshold in (30, 60):
            corrected = output_folder(model, threshold)
            for kind in ('predictions', 'metrics', 'calibration', 'intervals', 'bootstrap'):
                if kind == 'predictions':
                    old_file = original / 'predictions_realized_fh.csv'
                    left = pd.read_csv(old_file, float_precision='round_trip')
                    keys = ['spell_id', 'origin', 'horizon']
                else:
                    old_name = ('k2_intervals.csv' if model == 'A5' else 'intervals.csv') if kind == 'intervals' else (
                        'bootstrap_replicates.csv' if model == 'A5' else 'bootstrap.csv') if kind == 'bootstrap' else kind + '.csv'
                    old_file = original / old_name
                    left = pd.read_csv(old_file, float_precision='round_trip')
                    left = left[left.variant.eq('realized_fh')]
                    keys = ['model', 'pn'] if kind == 'metrics' else ['model', 'decil'] if kind == 'calibration' else (
                        ['pn'] if model == 'A5' else ['criterion', 'aggregation', 'pn']) if kind == 'intervals' else (
                        ['replicate'] if model == 'A5' else ['criterion', 'aggregation', 'replicate'])
                new_file = corrected / f'{kind}_realized_fh.csv'
                right = pd.read_csv(new_file, float_precision='round_trip')
                assert_same(left, right, keys)
                rows.append(dict(model=model, threshold=threshold, artifact=kind, exact=True,
                    rows=len(left), original_sha256=sha(old_file), corrected_sha256=sha(new_file)))
    atomic_json(ROOT / 'data/derived/exposure_errata_control_verification.json',
        dict(all_controls_exact=True, control='realized_fh', comparisons=rows))
    print('All 20 realized_fh control comparisons are exactly equal, including bootstrap draws.')


if __name__ == '__main__':
    main()
