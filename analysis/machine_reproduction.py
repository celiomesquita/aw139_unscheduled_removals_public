"""T17b/T17c: old-host artifacts only; local replays remain bitwise."""
import hashlib
import io
import math
import subprocess

import numpy as np
import pandas as pd

OLD_HOST_ATOL = 1e-8
OLD_HOST_RTOL = 1e-6
SIGNED_FIELDS = {'delta_log', 'ci_lo', 'ci_hi', 'simultaneous_lo', 'simultaneous_hi'}


def _float_check(a, b, column, report):
    np.testing.assert_array_equal(np.isnan(a), np.isnan(b))
    np.testing.assert_array_equal(np.isposinf(a), np.isposinf(b))
    np.testing.assert_array_equal(np.isneginf(a), np.isneginf(b))
    finite = np.isfinite(b)
    difference = np.abs(a[finite] - b[finite])
    ratios = difference / (OLD_HOST_ATOL + OLD_HOST_RTOL * np.abs(b[finite]))
    stats = dict(mode='T17c_float', max_abs_difference=float(np.max(difference, initial=0.)),
                 max_ratio=float(np.max(ratios, initial=0.)))
    report[column] = stats
    if not np.isclose(a[finite], b[finite], atol=OLD_HOST_ATOL, rtol=OLD_HOST_RTOL).all():
        raise AssertionError(f'T17c limit exceeded in {column}: {stats}')
    field = column.split('.')[-1]
    if (field in SIGNED_FIELDS or field.endswith(('_lo', '_hi', '_low', '_high'))
            or 'lower' in field or 'upper' in field):
        np.testing.assert_array_equal(np.sign(a[finite]), np.sign(b[finite]),
                                      err_msg='T17c: interval/effect sign changed')
    return stats['max_abs_difference']


def compare_old_frame(actual, expected, report=None):
    """Only old-host floats have tolerance; decisions, counts and signs are exact."""
    report = {} if report is None else report
    pd.testing.assert_index_equal(actual.index, expected.index)
    pd.testing.assert_index_equal(actual.columns, expected.columns)
    maximum = 0.
    for column in expected:
        left, right = actual[column], expected[column]
        if pd.api.types.is_float_dtype(right.dtype):
            if not pd.api.types.is_numeric_dtype(left.dtype):
                raise AssertionError(f'Non-numeric replacement: {column}')
            maximum = max(maximum, _float_check(left.to_numpy(float), right.to_numpy(float), column, report))
        else:
            pd.testing.assert_series_equal(left, right, check_dtype=True)
            report[column] = dict(mode='exact', max_abs_difference=0., max_ratio=0.)
    return maximum


def compare_old_json(actual, expected, report=None, path='root'):
    """Float leaves use T17c; hashes, labels, decisions and integers are exact."""
    report = {} if report is None else report
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise AssertionError('JSON keys changed')
        return max((compare_old_json(actual[k], v, report, path + '.' + k)
                    for k, v in expected.items()), default=0.)
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError('JSON list changed')
        return max((compare_old_json(a, b, report, path + '.' + str(i))
                    for i, (a, b) in enumerate(zip(actual, expected))), default=0.)
    if isinstance(expected, float):
        if type(actual) is not float:
            raise AssertionError('JSON float type changed')
        return _float_check(np.array([actual]), np.array([expected]), path, report)
    if type(actual) is not type(expected) or actual != expected:
        raise AssertionError('Exact JSON value changed: ' + path)
    report[path] = dict(mode='exact', max_abs_difference=0., max_ratio=0.)
    return 0.


def old_digest_matches(data, expected):
    """Input hashes have no numerical tolerance; only documented LF/CRLF."""
    return hashlib.sha256(data).hexdigest() == expected or (
        b'\0' not in data and hashlib.sha256(
            data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')).hexdigest() == expected)


def compare_old_csv_bytes(actual, expected, report=None):
    return compare_old_frame(pd.read_csv(io.BytesIO(actual), float_precision='round_trip'),
                             pd.read_csv(io.BytesIO(expected), float_precision='round_trip'), report)


def committed_old_bytes(root, name, expected_hash):
    data = subprocess.check_output(['git', 'show', '57e422b:' + name], cwd=root)
    if not old_digest_matches(data, expected_hash):
        raise AssertionError('Historical baseline hash differs: ' + name)
    return data

# T17d is an explicit, separate profile. A5 continues to use T17c above.
HIERARCHICAL_ATOL = 1e-4
SCIENTIFIC_FIELDS = {'delta_log', 'ci_lo', 'ci_hi', 'simultaneous_lo', 'simultaneous_hi'}
STRUCTURAL_FIELDS = {'n', 'predictions', 'risk_spells', 'aircraft', 'synthetic_spells',
                     'incomplete_fragments_excluded', 'unit_predictions',
                     'fallback_share', 'hW_fallback', 'hE_fallback',
                     'converged', 'attempts', 'boundary', 'zero_variance'}


def _hierarchical_numeric(a, b, column, report, *, exact=False, aggregate=None):
    np.testing.assert_array_equal(np.isnan(a), np.isnan(b))
    np.testing.assert_array_equal(np.isposinf(a), np.isposinf(b))
    np.testing.assert_array_equal(np.isneginf(a), np.isneginf(b))
    finite = np.isfinite(b)
    delta = np.abs(a[finite] - b[finite])
    nonzero = b[finite] != 0
    relative = delta[nonzero] / np.abs(b[finite][nonzero])
    maximum = float(np.max(delta, initial=0.))
    field = column.split('.')[-1]
    scientific = field in SCIENTIFIC_FIELDS
    ag = np.ones(len(delta), bool) if aggregate is None else np.asarray(aggregate, bool)[finite]
    bound_field = scientific and field != 'delta_log'
    bounded = (np.ones(len(delta), bool) if bound_field else ag) if scientific else np.zeros(len(delta), bool)
    limits = np.where(ag, HIERARCHICAL_ATOL, .5 * np.abs(b[finite]))
    ratios = np.divide(delta, limits, out=np.zeros_like(delta), where=limits != 0)
    zero_fail = bounded & (limits == 0) & (delta != 0)
    ratio = float(np.max(ratios[bounded], initial=0.)) if bounded.any() else None
    stats = dict(mode='exact' if exact else 'T17f_scientific' if bounded.any() else 'reported_only',
        max_abs_difference=maximum, max_relative_difference=float(np.max(relative, initial=0.)),
        zero_reference_changed=int(np.count_nonzero((~nonzero) & (delta != 0))),
        max_ratio=ratio, zero_margin_failures=int(zero_fail.sum()))
    if scientific:
        stats.update(aggregate_max_abs_difference=float(np.max(delta[ag], initial=0.)),
            aggregate_max_ratio=float(np.max(ratios[ag], initial=0.)) if ag.any() else None,
            pn_max_abs_difference=float(np.max(delta[~ag], initial=0.)),
            pn_bound_max_ratio=float(np.max(ratios[~ag], initial=0.)) if bound_field and (~ag).any() else None,
            pn_delta_log_reported_only=field == 'delta_log')
    report[column] = stats
    if exact:
        np.testing.assert_array_equal(a, b, err_msg='T17f: structural/convergence value changed')
    if zero_fail.any() or np.any(delta[bounded] > limits[bounded]):
        raise AssertionError(f'T17f scientific limit exceeded in {column}: {stats}')
    if (field in SIGNED_FIELDS or field.endswith(('_lo', '_hi', '_low', '_high'))
            or 'lower' in field or 'upper' in field):
        np.testing.assert_array_equal(np.sign(a[finite]), np.sign(b[finite]),
                                      err_msg='T17f: interval/effect sign changed')
    return maximum


def compare_hierarchical_frame(actual, expected, artifact, report=None):
    """T17d only for A4/A16; calibration observed is not a structural count."""
    report = {} if report is None else report
    pd.testing.assert_index_equal(actual.index, expected.index)
    pd.testing.assert_index_equal(actual.columns, expected.columns)
    maximum = 0.
    calibration = artifact.rsplit('/', 1)[-1].startswith('calibration')
    aggregate = expected.pn.eq('aggregate').to_numpy() if 'pn' in expected else None
    if 'pn' in expected:
        pd.testing.assert_series_equal(actual.pn, expected.pn, check_dtype=True)
    for column in expected:
        left, right = actual[column], expected[column]
        numeric = pd.api.types.is_numeric_dtype(right.dtype) and not pd.api.types.is_bool_dtype(right.dtype)
        reported_count = column in ('evaluations', 'successful_attempts') or column == 'observed' and calibration
        if numeric and (pd.api.types.is_float_dtype(right.dtype) or reported_count):
            if not pd.api.types.is_numeric_dtype(left.dtype):
                raise AssertionError('T17d non-numeric replacement: ' + column)
            maximum = max(maximum, _hierarchical_numeric(left.to_numpy(float), right.to_numpy(float),
                column, report, exact=column in STRUCTURAL_FIELDS, aggregate=aggregate))
        else:
            pd.testing.assert_series_equal(left, right, check_dtype=True)
            report[column] = dict(mode='exact', max_abs_difference=0., max_relative_difference=0.,
                                  zero_reference_changed=0, max_ratio=None)
    return maximum


def compare_hierarchical_csv_bytes(actual, expected, artifact, report=None):
    return compare_hierarchical_frame(pd.read_csv(io.BytesIO(actual), float_precision='round_trip'),
        pd.read_csv(io.BytesIO(expected), float_precision='round_trip'), artifact, report)


def compare_hierarchical_json(actual, expected, report=None, path='root'):
    """T17d summary: every categorical decision and structural integer is exact."""
    report = {} if report is None else report
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise AssertionError('T17d JSON keys changed')
        return max((compare_hierarchical_json(actual[k], v, report, path + '.' + k)
                    for k, v in expected.items()), default=0.)
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError('T17d JSON list changed')
        return max((compare_hierarchical_json(a, b, report, path + '.' + str(i))
                    for i, (a, b) in enumerate(zip(actual, expected))), default=0.)
    field = path.split('.')[-1]
    if isinstance(expected, float) or field in ('evaluations', 'successful_attempts'):
        if type(actual) is not type(expected):
            raise AssertionError('T17d numeric type changed: ' + path)
        return _hierarchical_numeric(np.array([actual], float), np.array([expected], float),
                                     path, report, exact=field in STRUCTURAL_FIELDS)
    if type(actual) is not type(expected) or actual != expected:
        raise AssertionError('T17d decision/structural value changed: ' + path)
    report[path] = dict(mode='exact', max_abs_difference=0., max_relative_difference=0.,
                       zero_reference_changed=0, max_ratio=None)
    return 0.


def compare_author_closure_frame(actual, expected, artifact, report=None):
    """Author's T17 closure: only decisions and interval signs can block.

    All other inter-host changes are descriptive. Local replay equality is
    enforced independently on bytes by the executor, never by this helper.
    """
    report = {} if report is None else report
    name = artifact.rsplit('/', 1)[-1]
    decisions = name.startswith('decision_') or name == 'decision.csv'
    intervals = name.startswith('intervals_') or name == 'intervals.csv'
    keys = [k for k in ('variant', 'aggregation', 'criterion', 'pn')
            if k in expected and (intervals or decisions)]
    a, b = actual, expected
    if intervals or decisions:
        if not keys or any(k not in actual for k in keys):
            raise AssertionError('Decision context unavailable: ' + artifact)
        if actual.duplicated(keys).any() or expected.duplicated(keys).any():
            raise AssertionError('Ambiguous decision context: ' + artifact)
        a, b = actual.set_index(keys).sort_index(), expected.set_index(keys).sort_index()
        if not a.index.equals(b.index):
            raise AssertionError('Decision contexts changed: ' + artifact)
        if decisions:
            if 'outcome' not in a or 'outcome' not in b or not a.outcome.equals(b.outcome):
                raise AssertionError('Scientific outcome changed: ' + artifact)
        if intervals:
            for field in ('ci_lo', 'ci_hi', 'simultaneous_lo', 'simultaneous_hi'):
                if field not in a or field not in b:
                    raise AssertionError('Interval decision unavailable: ' + artifact)
                left, right = a[field].to_numpy(float), b[field].to_numpy(float)
                if not np.array_equal(np.isnan(left), np.isnan(right)):
                    raise AssertionError('Interval decision undefined on one host: ' + artifact)
                if not np.array_equal(np.sign(left), np.sign(right), equal_nan=True):
                    raise AssertionError('Interval sign changed: ' + artifact + ':' + field)
    report['_schema'] = dict(mode='reported_only', historical_rows=len(expected), current_rows=len(actual),
        added_columns=sorted(set(actual.columns)-set(expected.columns)),
        removed_columns=sorted(set(expected.columns)-set(actual.columns)))
    maximum = 0.
    for column in b:
        if column not in a:
            report[column] = dict(mode='reported_only', unavailable_on_current=True)
            continue
        left, right = a[column].reset_index(drop=True), b[column].reset_index(drop=True)
        count = min(len(left), len(right))
        left, right = left.iloc[:count], right.iloc[:count]
        numeric = all(pd.api.types.is_numeric_dtype(x.dtype) for x in (left, right))
        if numeric:
            av, bv = left.to_numpy(float), right.to_numpy(float)
            finite = np.isfinite(av) & np.isfinite(bv)
            delta = np.abs(av[finite]-bv[finite]); nonzero = bv[finite] != 0
            absolute = float(np.max(delta, initial=0.)); maximum = max(maximum, absolute)
            report[column] = dict(mode='reported_only', max_abs_difference=absolute,
                max_relative_difference=float(np.max(delta[nonzero]/np.abs(bv[finite][nonzero]), initial=0.)),
                zero_reference_changed=int(np.count_nonzero((~nonzero) & (delta != 0))),
                changed_values=int(np.count_nonzero(~np.isclose(av,bv,rtol=0,atol=0,equal_nan=True))),
                nan_mask_changes=int(np.count_nonzero(np.isnan(av)!=np.isnan(bv))))
        else:
            equal = left.eq(right) | (left.isna() & right.isna())
            report[column] = dict(mode='reported_only', changed_values=int((~equal).sum()))
    return maximum


def compare_author_closure_csv_bytes(actual, expected, artifact, report=None):
    if not expected.strip() or not actual.strip():
        if report is not None:
            report['_empty_table'] = dict(mode='reported_only', historical_bytes=len(expected), current_bytes=len(actual))
        if artifact.rsplit('/',1)[-1].startswith(('decision_', 'intervals_')):
            raise AssertionError('Scientific decisions unavailable: ' + artifact)
        return 0.
    return compare_author_closure_frame(pd.read_csv(io.BytesIO(actual), float_precision='round_trip'),
        pd.read_csv(io.BytesIO(expected), float_precision='round_trip'), artifact, report)
