"""T15/T16 adapters preserve indexing, cache scope and fresh seed stream."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_REPOSITORY = (ROOT / 'paper' / 'manuscript.tex').exists() and (ROOT / 'docs').exists()
sys.path.insert(0, str(ROOT / 'analysis'))
import a16_flow17
from errata_exposicao import affected_counts, SharedThresholdTraining
from exposure_errata import CorrectedA4
from round5_execution import atomic_json, amendment006


class Prior:
    def __init__(self):
        self.calls = []

    def prepare(self, origin, variant):
        value = object()
        self.calls.append((origin, variant, value))
        return value


class Cached(SharedThresholdTraining, Prior):
    pass


class TestRound5Execution(unittest.TestCase):
    @unittest.skipUnless(PRIVATE_REPOSITORY, 'public package: requires the private manuscript, docs and Git history')
    def test_amendment006_is_committed_and_authorizes_the_current_rule(self):
        self.assertTrue(amendment006()['revision'].startswith('6848e19'))

    def test_threshold_cache_never_crosses_origin_or_variant(self):
        cache = Cached()
        first = cache.prepare('2025-01', 'principal')
        self.assertIs(first, cache.prepare('2025-01', 'principal'))
        self.assertIsNot(first, cache.prepare('2025-02', 'principal'))
        self.assertIsNot(first, cache.prepare('2025-01', 'provenance'))
        self.assertEqual(len(cache.calls), 3)

    def test_flow17_changes_only_study_seed_keyword(self):
        with patch.object(a16_flow17, 'original_synthetic_inputs', return_value='sentinel') as generator:
            result = a16_flow17.synthetic_flow17(3, 'truth', 'channels', copies=4,
                level='null', seed_study=16, seed_cell=5)
            self.assertEqual(result, 'sentinel')
            generator.assert_called_once_with(3, 'truth', 'channels', copies=4,
                level='null', seed_study=17, seed_cell=5)

    def test_corrected_cache_keeps_realized_and_principal_training_identical(self):
        instance = a16_flow17.CorrectedSharedTraining.__new__(a16_flow17.CorrectedSharedTraining)
        instance.common_training = {}
        value = object()
        with patch.object(CorrectedA4, 'prepare', return_value=value) as prepare:
            self.assertIs(instance.prepare('2025-01', 'principal'), value)
            self.assertIs(instance.prepare('2025-01', 'realized_fh'), value)
            self.assertEqual(prepare.call_count, 1)

    def test_affected_counts_ignore_added_diagnostic_columns(self):
        original = pd.DataFrame({'spell_id': ['S1'], 'pn': ['PN'], 'aircraft': ['AC-01'],
            'origin': ['2025-01-01'], 'horizon': [1], 'w_selected': [.2], 'e_selected': [.3],
            'baseline': [.1], 'w_selected_fallback': [False], 'e_selected_fallback': [False]})
        corrected = original.assign(observed_days_90d=90)
        row = affected_counts(original, corrected).iloc[0]
        self.assertEqual(row.any_probability_changed, 0)
        corrected.loc[0, 'w_selected'] = .4
        row = affected_counts(original, corrected).iloc[0]
        self.assertEqual(row.w_selected_changed, 1)
        self.assertEqual(row.e_selected_changed, 0)

    def test_atomic_write_retries_only_the_same_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'status.json'
            native = Path.replace
            calls = []
            def replace(path, other):
                calls.append(path.read_bytes())
                if len(calls) == 1:
                    raise PermissionError('transient file reader')
                return native(path, other)
            with patch.object(Path, 'replace', replace), patch('round5_execution.time.sleep'):
                atomic_json(target, {'replicate': 12})
            self.assertEqual(calls[0], calls[1])
            self.assertEqual(json.loads(target.read_text()), {'replicate': 12})


if __name__ == '__main__':
    unittest.main()
