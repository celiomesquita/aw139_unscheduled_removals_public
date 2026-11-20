"""Prospective two-point regret verification; never accepts partial references."""
import gc
import json
import math
import time
from unittest.mock import patch
import numpy as np
from a9_static_fast import FastCalendarRenewal
from amendment015.age import calibrate,require_manifest
from amendment015.disk import DiskCalendarRenewal
from amendment015.state import ROOT,OUT,atomic,digest,freeze,ledger,check_deadline,utcnow
from amendment015.references import check_sources


def point_rate(item,age):
    """Historical calendar transitions/stationarity at one prescribed common age."""
    model=item['model'];rates=[];omitted=0;mass=[];tail_p=[];tail_d=[]
    calendar_type=DiskCalendarRenewal if item['id']=='06' else FastCalendarRenewal
    for context in item['contexts']:
        check_deadline()
        daily=np.asarray(context['daily'],float)
        if not len(context['visits']) or daily.sum()==0:
            omitted+=1
            if age==0 and len(context['visits']) and daily.sum()==0:
                rates.append(float(context.get('weight',1.))*len(set(context['visits']))/len(daily))
            continue
        # The 24h cap ends with certified references; verification uses the 336h cap.
        with patch('amendment015.disk.check_deadline',lambda **kwargs:check_deadline(refresh=False)):
            calendar=calendar_type(daily,context['visits'],model['beta'],model['eta'],model['nu'],item['r'],float(context.get('weight',1.)),4)
        for phase,row in enumerate(calendar.rows):
            row['cursor']=int(np.searchsorted(row['clock'][row['stops']],age,side='left'))
            calendar.replace_row(phase,update_inverse=False)
        calendar.refactor()
        rates.append(calendar.rate());mass.append(calendar.mass_error)
        tail_p.append(calendar.max_tail_probability);tail_d.append(calendar.max_tail_duration)
        del calendar;gc.collect()
    return sum(rates),dict(probability_mass_error=max(mass,default=0.),
        tail_probability_bound=max(tail_p,default=0.),tail_duration_bound=max(tail_d,default=0.),
        omitted_threshold_independent_groups=omitted,subdivisions=4,
        method='same historical transitions and stationary solver; direct policy at one prescribed age')


def run():
    manifest_path=OUT/'references/manifest.json'
    manifest=require_manifest(manifest_path)
    config=json.loads((OUT/'configuration.json').read_text());check_sources(config)
    sources={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'analysis/amendment015/verification.py',ROOT/'analysis/amendment015/disk.py']}
    freeze(OUT/'verification_configuration.json',dict(reference_manifest_sha256=digest(manifest_path),
        configuration_sha256=digest(OUT/'configuration.json'),sources=sources,N=9,g_max=.005,g_negative_stop=-1e-8,
        numerical_method_unchanged=True,sample_unchanged=True))
    value=ledger('calibration_verification')
    value.setdefault('reference_block_finished_utc',value['updated_utc'])
    from datetime import datetime
    value['reference_block_wall_seconds']=(datetime.fromisoformat(value['reference_block_finished_utc'])-datetime.fromisoformat(value['reference_preparation_start_utc'])).total_seconds()
    atomic(OUT/'time_ledger.json',value)
    records=[];informative=False
    for item in config['sample']:
        check_deadline();require_manifest(manifest_path)
        cert=json.loads((OUT/'references'/f"{item['id']}_certificate.json").read_text())
        if cert['input_sha256']!=digest(OUT/'references'/f"{item['id']}_inputs.json"):raise RuntimeError('REFERENCE_INPUT_MISMATCH')
        for source,h in cert['evaluator_sha256'].items():
            if digest(ROOT/source)!=h:raise RuntimeError('REFERENCE_EVALUATOR_MISMATCH')
        model=item['model'];informative|=model['beta']>1
        atomic(OUT/'verification_progress.json',dict(id=item['id'],stage='cheap_age',utc=utcnow().isoformat()))
        wall=time.perf_counter()
        cheap,diagnostic=calibrate(item['contexts'],model['beta'],model['eta'],model['nu'],item['r'],manifest_path=manifest_path)
        exact=math.inf if cert['infinite'] else cert['age']
        atomic(OUT/'verification_progress.json',dict(id=item['id'],stage='two_exact_points',utc=utcnow().isoformat()))
        qc,dc=point_rate(item,cheap);qe,de=point_rate(item,exact)
        branch_same=math.isinf(cheap)==math.isinf(exact)
        if qe==0:
            g=0. if qc==0 else None
        else:g=(qc-qe)/qe
        shift=0. if math.isinf(cheap) and math.isinf(exact) else (None if not branch_same else abs(cheap-exact))
        relative_shift=(None if shift is None or exact==0 else (0. if math.isinf(exact) else shift/abs(exact)))
        passed=branch_same and g is not None and -1e-8<=g<=.005
        record=dict(id=item['id'],pn=item['pn'],r=item['r'],scale=model['scale'],
            cheap_age=None if math.isinf(cheap) else cheap,cheap_infinite=math.isinf(cheap),
            exact_age=None if math.isinf(exact) else exact,exact_infinite=math.isinf(exact),
            absolute_age_displacement=shift,relative_age_displacement=relative_shift,
            Q_cheap=qc,Q_exact=qe,certificate_rate=cert['rate'],point_minus_certificate_rate=qe-cert['rate'],g=g,
            branch_same=branch_same,passed=passed,cheap_diagnostics=diagnostic,
            cheap_point_diagnostics=dc,exact_point_diagnostics=de,wall_seconds=time.perf_counter()-wall)
        records.append(record)
        atomic(OUT/'verification'/f"{item['id']}.json",record)
        atomic(OUT/'verification.json',dict(status='running' if passed else 'failed',completed=len(records),N=9,records=records,
            reference_manifest_sha256=digest(manifest_path),tolerance_retuned=False))
        if not passed:raise ArithmeticError('CALIBRATION_VERIFICATION_FAILED:'+item['id'])
    if not informative:raise ArithmeticError('NO_INFORMATIVE_AGEING_CASE')
    freeze(OUT/'verification_manifest.json',dict(status='passed',N=9,records=records,
        reference_manifest_sha256=digest(manifest_path),configuration_sha256=digest(OUT/'verification_configuration.json')))
    ledger('calibration_verified')
    return records
