"""Operational parallelism keeps checkpoints and scientific integrity rules."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
import a16_multicore as parallel


class TestA16Multicore(unittest.TestCase):
    def test_native_threads_are_limited_before_spawn(self):
        with patch.dict(os.environ):
            parallel.native_threads_one()
            for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
                self.assertEqual(os.environ[key], '1')

    def test_completed_failure_is_reused_and_changed_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(parallel, 'OUT', Path(directory)):
            folder = Path(directory) / 'replicas' / 'null_x1' / '000'
            folder.mkdir(parents=True)
            data = folder / 'diagnostic.csv'
            data.write_text('value\n1\n', encoding='utf-8')
            record = dict(cell='null_x1', replicate=0, variants={'principal': {'status': 'failed'}},
                          artifacts={'diagnostic.csv': parallel.sha(data)})
            (folder / 'summary.json').write_text(json.dumps(record), encoding='utf-8')
            self.assertEqual(parallel.checkpoint({'id': 'null_x1'}, 0), record)
            self.assertIsNone(parallel.checkpoint({'id': 'null_x1'}, 1))
            data.write_text('value\n2\n', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                parallel.checkpoint({'id': 'null_x1'}, 0)

    def test_editorial_changes_are_distinguished_from_scientific_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'manifest.json').write_text('{"inputs": {}}', encoding='utf-8')
            config = {'protected': {parallel.MANUSCRIPT: 'original', 'data/derived/a4/test.csv': 'science',
                                   'analysis/preregistro_A16_A9.md': 'protocol'}}
            current = {parallel.MANUSCRIPT: 'external-edit', 'data/derived/a4/test.csv': 'science'}
            with patch.object(parallel.core, 'check_sources'), patch.object(parallel.core, 'GENERATOR', folder), \
                 patch.object(parallel.core, 'committed_protocol', return_value=('revision', 'protocol')), \
                 patch.object(parallel, 'protected_hashes', return_value=current):
                result = parallel.integrity(config)
                self.assertTrue(result['scientific_artifacts_unchanged'])
                self.assertTrue(result['manuscript_changed_externally'])
                current['data/derived/a4/test.csv'] = 'changed'
                with self.assertRaises(RuntimeError):
                    parallel.integrity(config)

    def test_verification_ignores_timing_but_covers_scientific_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'summary.json').write_text('{}', encoding='utf-8')
            (folder / 'runtime.json').write_text('{"seconds": 1}', encoding='utf-8')
            first = parallel.scientific_snapshot(folder)
            (folder / 'runtime.json').write_text('{"seconds": 100}', encoding='utf-8')
            self.assertEqual(first, parallel.scientific_snapshot(folder))
            (folder / 'summary.json').write_text('{"changed": true}', encoding='utf-8')
            self.assertNotEqual(first, parallel.scientific_snapshot(folder))


if __name__ == '__main__':
    unittest.main()
