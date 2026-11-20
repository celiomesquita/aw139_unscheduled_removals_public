"""T14: verify that frozen training modes and generator do not use forecast rates."""
import ast
import inspect
import json
from pathlib import Path
import textwrap
from unittest.mock import patch

import numpy as np
import pandas as pd

from a16_generator import ROOT, OUT as GENERATOR, load_design, sha
from a4_validation import HierarchicalEvaluation
from a5_models import Exposure, training_view
from a5_validation import Evaluation


def rate_calls(function):
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    return [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == 'rates']


def main():
    functions = (training_view, Evaluation.prepare, HierarchicalEvaluation.prepare,
                 Exposure.clocks, Exposure.ages, Exposure.incomplete)
    audit = {function.__qualname__: rate_calls(function) for function in functions}
    if any(audit.values()):
        raise RuntimeError('STOP: training/exposure ages depend on forecast rates')
    effects_path = ROOT / 'data/derived/a4/effects.csv'
    effects = pd.read_csv(effects_path, float_precision='round_trip')
    keys = ['origin', 'pn', 'model']
    principal = effects[effects.variant.eq('principal')].drop(columns='variant').sort_values(keys).reset_index(drop=True)
    realized = effects[effects.variant.eq('realized_fh')].drop(columns='variant').sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(principal, realized, check_exact=True)
    with patch.object(Exposure, 'rates', side_effect=AssertionError('Forecast rates must not enter generator')):
        truth, observed, _, _, _, _ = load_design()
    original_truth = pd.read_csv(GENERATOR / 'truth.csv', float_precision='round_trip')
    pd.testing.assert_frame_equal(truth, original_truth, check_exact=True)
    original_observed = pd.read_csv(GENERATOR / 'observed_rates.csv', float_precision='round_trip')
    pd.testing.assert_frame_equal(observed, original_observed, check_exact=True)
    generator_manifest = json.loads((GENERATOR / 'manifest.json').read_text(encoding='utf-8'))
    for name, digest in generator_manifest['outputs'].items():
        if sha(GENERATOR / name) != digest:
            raise RuntimeError('Generator validation artifact changed: ' + name)
    results = dict(training_functions_without_forecast_rates=audit,
        all_origins_effects_identical_principal_realized_fh=True,
        last_origin='2025-12-01', last_origin_rows=int(principal.origin.eq('2025-12-01').sum()),
        generator_load_succeeds_when_forecast_rates_raise=True,
        generator_truth_exactly_preserved=True, observed_rates_exactly_preserved=True,
        generator_validation_artifacts_unchanged=True, generator_gate_remains_valid=True,
        real_models_refitted=0, corrected_results_produced=False,
        effects_sha256=sha(effects_path), generator_manifest_sha256=sha(GENERATOR / 'manifest.json'))
    destination = ROOT / 'data/derived/a16/exposure_independence.json'
    destination.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Training modes and generator independent of forecast exposure; original validation preserved.')


if __name__ == '__main__':
    main()
