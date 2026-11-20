"""T5: dependency order and deterministic replay of the entire real-data flow."""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
PRIVATE_REPOSITORY = (ROOT / 'paper' / 'manuscript.tex').exists() and (ROOT / 'docs').exists()
sys.path.insert(0,str(ROOT/'analysis'))
from run_all import STEPS,snapshot
from machine_reproduction import committed_old_bytes, compare_old_csv_bytes


class TestPipeline(unittest.TestCase):
    def test_dependencies_are_ordered_and_no_future_model_is_run(self):
        seen=set()
        for script,deps in STEPS:
            self.assertTrue(set(deps)<=seen,script)
            self.assertNotIn('a4',script.lower())
            self.assertNotIn('solver',script.lower())
            seen.add(script)
        self.assertEqual(len(seen),len(STEPS))
        self.assertEqual(STEPS[-1][0],'a5_validation.py')

    @unittest.skipUnless(PRIVATE_REPOSITORY, 'public package: requires the private manuscript, docs and Git history')
    def test_complete_pipeline_twice_identical(self):
        protected=[ROOT/'paper'/'manuscript.tex',ROOT/'analysis'/'preregistro_A5.md',
                   ROOT/'analysis'/'preregistro_A4.md']
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        def run():
            result=subprocess.run([sys.executable,str(ROOT/'analysis'/'run_all.py')],cwd=ROOT,
                capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            files=snapshot()
            files['data/derived/pipeline_manifest.json']=hashlib.sha256(
                (ROOT/'data'/'derived'/'pipeline_manifest.json').read_bytes()).hexdigest()
            return files
        first,second=run(),run()
        self.assertEqual(first,second)
        self.assertEqual((ROOT/'data'/'derived'/'a5'/'manifest.json').read_bytes(),
                         (ROOT/'analysis'/'audit'/'a5_initial_manifest.json').read_bytes())
        metadata=json.loads((ROOT/'data'/'derived'/'pipeline_manifest.json').read_text(encoding='utf-8'))
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        self.assertEqual(metadata['execution_git_revision'],head)
        self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
        initial=json.loads((ROOT/'analysis'/'audit'/'a5_initial_output_hashes.json').read_text(encoding='utf-8'))
        scientific={name:digest for name,digest in initial.items() if name.endswith('.csv')}
        # T17b: old-host CSVs only; first == second above remains bitwise.
        old_host_checks = {}
        for name,digest in scientific.items():
            old = committed_old_bytes(ROOT, name, digest)
            old_host_checks[name] = {}
            try:
                compare_old_csv_bytes((ROOT/name).read_bytes(), old, old_host_checks[name])
            finally:
                (ROOT/'data/derived/old_host_pipeline_comparisons.json').write_text(
                    json.dumps(old_host_checks, indent=2, sort_keys=True)+'\n')
        for name in first:
            if name.endswith('.csv') and name not in scientific:
                old = subprocess.check_output(['git','show','57e422b:'+name], cwd=ROOT)
                old_host_checks[name] = {}
                try:
                    compare_old_csv_bytes((ROOT/name).read_bytes(), old, old_host_checks[name])
                finally:
                    (ROOT/'data/derived/old_host_pipeline_comparisons.json').write_text(
                        json.dumps(old_host_checks, indent=2, sort_keys=True)+'\n')
        proof=dict(full_runs=2,steps=len(STEPS),identical_artifacts=len(first),
                   protected_files_unchanged=True,a5_numerical_artifacts_unchanged=len(scientific),
                   old_host_column_comparisons=old_host_checks,sha256=second)
        (ROOT/'data'/'derived'/'pipeline_verification.json').write_text(
            json.dumps(proof,indent=2,sort_keys=True)+'\n',encoding='utf-8')


if __name__=='__main__':
    unittest.main()
