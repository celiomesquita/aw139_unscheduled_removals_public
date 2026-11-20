import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
from amendment015.fresh import admits,ALLOCATION
from amendment015.readonly_progress import ReadOnlyProgress

class TestFreshReference(unittest.TestCase):
    def test_admission_counts_existing_retained_rss(self):
        self.assertTrue(admits(ALLOCATION-100,100))
        self.assertFalse(admits(ALLOCATION-100,101))
        self.assertFalse(admits(15*2**30,2*2**30))

    def test_readonly_sampler_preserves_exact_bytes(self):
        from a9_static_fast import exhaustive_threshold
        contexts=[dict(daily=[1.,0.,2.,1.],visits=[0,2],weight=2.)]
        args=(contexts,2.,3.,.05,5.,4)
        before=exhaustive_threshold(*args)
        with tempfile.TemporaryDirectory() as folder:
            observer=ReadOnlyProgress(dict(id='toy',contexts=contexts),interval=.001,path=Path(folder)/'progress.json')
            observer.start()
            try:after=exhaustive_threshold(*args)
            finally:observer.stop(True)
            progress=json.loads((Path(folder)/'progress.json').read_text())
            self.assertEqual(progress['phases_fraction'],1.)
            self.assertEqual(progress['breakpoints_fraction'],1.)
        def bits(value):return struct.pack('<d',value[0])+json.dumps(value[1],sort_keys=True).encode()
        self.assertEqual(bits(before),bits(after))
