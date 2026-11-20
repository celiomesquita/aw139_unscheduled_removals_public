"""Replay the authorised real-data analysis DAG; never run A4 or the old solver.

Run: py -3 analysis/run_all.py. Historical protocols are replayed to preserve
their artifacts, not reinstated as the current scientific method.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DERIVED=ROOT/'data'/'derived'
STEPS=(
    ('feasibility.py',()),
    ('time_scales.py',('feasibility.py',)),
    ('inspection_censoring.py',('feasibility.py',)),
    ('inspection_evidence.py',('inspection_censoring.py',)),
    ('removal_labels.py',('feasibility.py',)),
    ('removal_review.py',('removal_labels.py',)),
    ('extended_review.py',('removal_review.py',)),
    ('event_costs.py',('feasibility.py',)),
    ('labour_attribution.py',('event_costs.py',)),
    ('round2_survival.py',('feasibility.py',)),
    ('round2_costs.py',('event_costs.py',)),
    ('a5_validation.py',('round2_survival.py','extended_review.py','round2_costs.py')),
)
REPORTS=('feasibility_report.md','time_scales_report.md','inspection_censoring_report.md',
    'inspection_evidence_report.md','removal_labels_report.md','removal_review_report.md',
    'extended_review_report.md','event_costs_report.md','labour_attribution_report.md',
    'round2_survival_report.md','round2_costs_report.md','a5_report.md')
CSV_OUTPUTS=('removals_clean.csv','spells.csv','weibull_by_pn.csv','weibull_by_pn_sensitivity.csv',
    'aircraft_fh_daily.csv','recurrent_tasks.csv','stoppages.csv',
    'time_scale_fits.csv','time_scale_coverage.csv','time_scale_choices.csv',
    'time_scale_broad_fits.csv','time_scale_broad_coverage.csv','time_scale_broad_choices.csv',
    'inspection_intervals.csv','inspection_weibull_fits.csv','inspection_evidence.csv',
    'removal_label_audit.csv','removal_label_evidence.csv','removal_label_summary.csv',
    'removal_review_evidence.csv','removal_review_queue.csv','missing_source_documents.csv',
    'extended_review_results.csv','present_document_evidence_gaps.csv','adjudication_status.csv',
    'event_cost_inputs.csv','document_labour_proxies.csv','return_to_flight_gaps.csv',
    'task_removal_labour_links.csv','task_labour_ledger.csv','event_labour_attribution.csv',
    'round2_inspection_bounds.csv','round2_weibull_fits.csv','k1_candidates.csv',
    'single_removal_cost_documents.csv','single_removal_mh_summary.csv','visit_gap_summary.csv')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_revision():
    try:
        return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        return 'not a git checkout'


def output_paths():
    files=[DERIVED/p for p in CSV_OUTPUTS]
    files += [ROOT/'analysis'/p for p in REPORTS]
    files += [ROOT/'config'/'cost_parameters.csv']
    files += sorted((DERIVED/'a5').glob('*.csv'))+[DERIVED/'a5'/'manifest.json']
    return files


def snapshot():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in output_paths()}


def run():
    completed=set()
    # Public package: the manuscript is not distributed, so only existing protected files are checked.
    protected=[p for p in [ROOT/'analysis'/'preregistro_A5.md',ROOT/'paper'/'manuscript.tex'] if p.exists()]
    protected += [p for p in [ROOT/'analysis'/'preregistro_A4.md'] if p.exists()]
    original={p:sha(p) for p in protected}
    for script,dependencies in STEPS:
        if not set(dependencies)<=completed:
            raise ValueError('Unmet analysis dependencies: '+script)
        print('Running '+script,flush=True)
        result=subprocess.run([sys.executable,str(ROOT/'analysis'/script)],cwd=ROOT,
                              capture_output=True,text=True,encoding='utf-8')
        if result.returncode:
            raise RuntimeError(script+' failed:\n'+result.stderr)
        completed.add(script)
    if any(sha(p)!=digest for p,digest in original.items()):
        raise ValueError('A protected preregistration or manuscript changed')
    outputs=snapshot()
    inputs=list((ROOT/'data'/'anonymised').glob('*.csv'))
    inputs += [ROOT/'config'/'rotor_inspection_map.csv']
    inputs += sorted((ROOT/'analysis').glob('*decisions.csv'))
    inputs += [ROOT/'analysis'/'preregistro_A5.md',ROOT/'analysis'/'emenda_A5_001.md']
    inputs += [ROOT/'analysis'/'audit'/'a5_initial_manifest.json']
    sources=[ROOT/'analysis'/script for script,_ in STEPS]
    sources += [ROOT/'analysis'/'a5_models.py',Path(__file__).resolve()]
    import pandas as pd
    decision=pd.read_csv(DERIVED/'a5'/'decision.csv')
    principal=decision.loc[decision.variant.eq('principal'),'outcome'].item()
    manifest=dict(steps=[s for s,_ in STEPS],
        execution_git_revision=git_revision(),
        inputs={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
        code={p.relative_to(ROOT).as_posix():sha(p) for p in sources},outputs=outputs,
        historical_steps=['time_scales.py','inspection_censoring.py','inspection_evidence.py'],
        k2_principal=principal,a4_executed=False,a7_executed=False)
    (DERIVED/'pipeline_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'Completed {len(STEPS)} steps; {len(outputs)} outputs; A4/A7 not run.',flush=True)
    return outputs


if __name__=='__main__':
    run()
