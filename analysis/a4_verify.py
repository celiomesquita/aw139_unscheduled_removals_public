"""Expensive A4 acceptance check: repeat full validation, compare every artifact."""
import hashlib
import json
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import scipy

from feasibility import ROOT,DERIVED
from a4_validation import OUT,VARIANTS


def snapshot():
    paths=sorted(p for p in OUT.iterdir() if p.is_file())+[ROOT/'analysis'/'a4_report.md',ROOT/'config'/'a4_scale_map.csv']
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def environment():
    result=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
        scipy=scipy.__version__,execution_git_revision=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (OUT/'environment.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def validate():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT/'analysis'/'preregistro_A4.md').read_bytes()).hexdigest()==manifest['preregistration_sha256']
    checks=[]
    cols=['w_selected','e_selected','baseline']
    for variant in VARIANTS:
        f=pd.read_csv(OUT/('predictions_'+variant+'.csv'))
        assert not f.duplicated(['spell_id','origin','horizon']).any()
        assert f.origin.nunique()==12 and set(f.horizon)=={1,2,3}
        p=f[cols].to_numpy()
        assert np.isfinite(p).all() and (p>=0).all() and (p<=1).all()
        differences=f.sort_values(['spell_id','origin','horizon']).groupby(['spell_id','origin'])[cols].diff().dropna()
        assert (differences>=-1e-12).all().all()
        checks.append(dict(variant=variant,rows=len(f),probabilities_valid=True,monotone_horizons=True))
    a5=pd.read_csv(DERIVED/'a5'/'predictions_principal.csv')
    a4=pd.read_csv(OUT/'predictions_principal.csv')
    keys=['spell_id','origin','horizon']
    joined=a4.merge(a5[keys+['y','baseline']],on=keys,suffixes=('_a4','_a5'),validate='one_to_one')
    assert len(joined)==len(a5)==len(a4)
    np.testing.assert_array_equal(joined.y_a4,joined.y_a5)
    np.testing.assert_allclose(joined.baseline_a4,joined.baseline_a5,rtol=0,atol=1e-14)
    return checks


def main():
    environment()
    checks=validate()
    first=snapshot()
    subprocess.run([sys.executable,str(ROOT/'analysis'/'a4_validation.py')],cwd=ROOT,check=True)
    environment()
    second=snapshot()
    assert first==second,[p for p in first if first[p]!=second.get(p)]
    validate()
    proof=dict(full_runs=2,identical_artifacts=len(first),preregistration_unchanged=True,
        baseline_and_targets_equal_a5=True,predictions=checks,sha256=second)
    (DERIVED/'a4_verification.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('A4 reproduced:',len(first),'identical artifacts',flush=True)


if __name__=='__main__':main()
