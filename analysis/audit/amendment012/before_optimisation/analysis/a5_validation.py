"""A5_v1: nested temporal evaluation; no optimisation or manual adjudication."""
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

from feasibility import ROOT, DERIVED, ANONYMISED, load_omth
from a5_models import Exposure, SCALES, START, END, training_view, fit_survival, incidence, realized_incidence

SEED=20261112
VARIANTS=('principal','realized_fh','imputed_takeoffs','inspection_intervals','provenance','no_admin')
MODELS=tuple(f'{k}_{s}' for k in ('w','e') for s in SCALES)+('baseline',)
OUT=DERIVED/'a5'
ADMIN_IDS=('R00173','R00293','R00294','R00328')
KEYS=['Part #','Serial #','Aircraft #','att','rem']


def log_score(y,p):
    p=np.clip(np.asarray(p,float),1e-12,1-1e-12)
    y=np.asarray(y,float)
    return y*np.log(p)+(1-y)*np.log1p(-p)


def installation_provenance(spells,removals):
    installs=removals.dropna(subset=['Attached Part #','Attached Serial #','Aircraft #','rem'])[
        ['Attached Part #','Attached Serial #','Aircraft #','rem']].rename(columns={
        'Attached Part #':'Part #','Attached Serial #':'Serial #','rem':'record_date'})
    joined=spells[['spell_id','Part #','Serial #','Aircraft #','att']].merge(
        installs,on=['Part #','Serial #','Aircraft #'],how='left')
    joined['record_date']=pd.to_datetime(joined.record_date)
    joined=joined[(joined.record_date-joined.att).abs().dt.days.le(3)]
    return joined.groupby('spell_id').record_date.min()


class Evaluation:
    def __init__(self,spells,flights,candidates,tasks,mapping,removals,admin_keys):
        self.spells=spells[spells.source.isin(['in_window_removed','in_window_censored']) &
                           spells['Part #'].isin(candidates)].copy()
        if 'spell_id' not in self.spells:
            self.spells['spell_id']=['S'+str(i).zfill(6) for i in self.spells.index]
        self.spells=self.spells.sort_values('spell_id').reset_index(drop=True)
        self.spells['pn']=self.spells['Part #']
        self.exposure=Exposure(flights)
        self.candidates=sorted(candidates)
        self.tasks=tasks
        self.mapping=mapping
        self.known=installation_provenance(self.spells,removals)
        admin=pd.MultiIndex.from_frame(admin_keys[KEYS])
        self.spells['admin_exclusion']=pd.MultiIndex.from_frame(self.spells[KEYS]).isin(admin)
        self.fits=[]
        self.selections=[]

    def cohort(self,origin,variant):
        x=self.spells
        if variant=='no_admin':
            x=x[~x.admin_exclusion]
        if variant=='provenance':
            x=x[x.spell_id.map(self.known).lt(origin)]
        return x

    def prepare(self,origin,variant):
        x=self.cohort(origin,variant)
        train=training_view(x,origin)
        risk=x[x.att.lt(origin)&x.rem.ge(origin)].copy()
        cutoff=origin-pd.Timedelta(days=1)
        clock=self.exposure.clocks(origin,variant=='imputed_takeoffs')
        positive=train.days.gt(0)
        pooled_days=float(train.loc[positive,'days'].sum())
        lam=float(train.loc[positive,'train_event'].sum()/pooled_days) if pooled_days else 0.
        nu_global=float(train.loc[positive,'competing'].sum()/pooled_days) if pooled_days else 0.
        nu={}
        fitted={}
        for pn in self.candidates:
            g=train[train.pn.eq(pn)]
            gp=g[g.days.gt(0)]
            denominator=float(gp.days.sum())
            nu[pn]=float(gp.competing.sum()/denominator) if denominator else nu_global
            for scale in SCALES:
                upper=self.exposure.ages(g,g.end,clock,scale)
                eligible=np.ones(len(g),bool)
                if scale=='takeoffs':
                    eligible=~self.exposure.incomplete(g,g.end,clock,'missing_cycles')
                lower=upper.copy()
                interval=np.zeros(len(g),bool)
                if variant=='inspection_intervals' and pn in set(self.mapping.pn):
                    for j,(_,row) in enumerate(g.iterrows()):
                        if not row.train_event:
                            continue
                        relevant=self.tasks[(self.tasks['Aircraft #']==row['Aircraft #']) &
                            self.tasks['Task #'].isin(self.mapping.loc[self.mapping.pn.eq(pn),'task']) &
                            self.tasks.d.ge(row.att)&self.tasks.d.lt(row.end)&self.tasks.d.le(cutoff)]
                        last=relevant.d.max() if not relevant.empty else row.att
                        lower[j]=self.exposure.ages(g.iloc[[j]],[last],clock,scale)[0]
                        interval[j]=0<=lower[j]<upper[j]
                for kind,prefix in [('weibull','w'),('exponential','e')]:
                    fit=fit_survival(upper[eligible],g.train_event.to_numpy()[eligible],kind,
                                     lower[eligible],interval[eligible])
                    fitted[(pn,prefix,scale)]=fit
                    self.fits.append(dict(variant=variant,origin=origin,pn=pn,model=prefix,
                        scale=scale,train_spells=len(g),incomplete_excluded=int((~eligible).sum()),
                        pooled_rate=lam,competing_rate=nu[pn],competing_pooled_fallback=not bool(denominator),
                        **fit))
        return train,risk,clock,lam,nu,fitted

    def forecast(self,origin,variant):
        train,risk,clock,lam,nu,fitted=self.prepare(origin,variant)
        if risk.empty:
            return pd.DataFrame()
        cutoff=origin-pd.Timedelta(days=1)
        rate_hours=self.exposure.rates(clock,origin,'Hours')
        rate_cycles=self.exposure.rates(clock,origin,'cycles')
        known_hours=self.exposure.rates(clock,origin,'known_hours')*90
        missing_hours=self.exposure.rates(clock,origin,'missing_hours')*90
        missing_cycles=self.exposure.rates(clock,origin,'missing_cycles')*90
        frames=[]
        for horizon in (1,2,3):
            end=origin+pd.DateOffset(months=horizon)
            if end-pd.Timedelta(days=1)>END:
                continue
            days=(end-origin).days
            out=risk[['spell_id','pn','Aircraft #']].rename(columns={'Aircraft #':'aircraft'}).copy()
            out['origin'],out['target_end'],out['horizon']=origin,end,horizon
            out['y']=(risk.event.eq(1)&risk.rem.lt(end)).astype(int).to_numpy()
            out['competing_observed']=(risk.event.eq(0)&risk.source.eq('in_window_removed')&risk.rem.lt(end)).to_numpy()
            comp=risk.pn.map(nu).to_numpy(float)
            baseline=(lam*(-np.expm1(-(lam+comp)*days))/(lam+comp)
                      if lam>0 else np.zeros(len(risk)))
            out['baseline']=baseline
            out['missing_hours_90d']=risk['Aircraft #'].map(missing_hours).to_numpy()
            incomplete_cycles=self.exposure.incomplete(risk,[cutoff]*len(risk),clock,'missing_cycles')
            cycles_unavailable=incomplete_cycles | risk['Aircraft #'].map(missing_cycles).gt(0).to_numpy()
            out['takeoffs_complete']=~cycles_unavailable
            for prefix in ('w','e'):
                for scale in SCALES:
                    name=f'{prefix}_{scale}'
                    probs=baseline.copy()
                    fallback=np.ones(len(risk),bool)
                    reasons=np.full(len(risk),'insufficient_events_or_fit',dtype=object)
                    age=self.exposure.ages(risk,[cutoff]*len(risk),clock,scale)
                    rate=(np.ones(len(risk)) if scale=='calendar' else
                          risk['Aircraft #'].map(rate_hours if scale=='FH' else rate_cycles).to_numpy(float))
                    for pn in self.candidates:
                        positions=np.flatnonzero(risk.pn.eq(pn).to_numpy())
                        fit=fitted[(pn,prefix,scale)]
                        if not len(positions) or not fit['converged']:
                            continue
                        eligible=positions
                        if scale=='takeoffs':
                            eligible=positions[~cycles_unavailable[positions]]
                            reasons[positions[cycles_unavailable[positions]]]='incomplete_takeoffs'
                        if scale=='FH':
                            no_rate=risk.iloc[positions]['Aircraft #'].map(known_hours).le(0).to_numpy()
                            unavailable=positions[no_rate]
                            eligible=positions[~no_rate]
                            calendar=fitted[(pn,prefix,'calendar')]
                            if len(unavailable) and calendar['converged']:
                                ca=self.exposure.ages(risk.iloc[unavailable],[cutoff]*len(unavailable),clock,'calendar')
                                probs[unavailable]=incidence(ca,1.,days,calendar['beta'],calendar['eta'],nu[pn])
                                reasons[unavailable]='calendar_no_hours_rate'
                        if not len(eligible):
                            continue
                        if variant=='realized_fh' and scale=='FH':
                            dates=pd.date_range(origin,end-pd.Timedelta(days=1))
                            exposures=clock['daily']['Hours'].loc[dates,risk.iloc[eligible]['Aircraft #']].to_numpy()
                            probs[eligible]=realized_incidence(age[eligible],exposures,
                                fit['beta'],fit['eta'],nu[pn])[-1]
                        else:
                            probs[eligible]=incidence(age[eligible],rate[eligible],days,
                                fit['beta'],fit['eta'],nu[pn])
                        fallback[eligible]=False
                        reasons[eligible]='fitted'
                    out[name]=probs
                    out[name+'_fallback']=fallback
                    out[name+'_reason']=reasons
            out['variant']=variant
            frames.append(out)
        return pd.concat(frames,ignore_index=True)

    def select(self,frame,past,variant,origin):
        if frame.empty:
            return frame
        available=(pd.concat(past,ignore_index=True) if past else pd.DataFrame())
        if not available.empty:
            available=available[available.target_end.le(origin-pd.Timedelta(days=1))]
        for prefix in ('w','e'):
            selected=np.empty(len(frame),object)
            pred=np.zeros(len(frame))
            fb=np.ones(len(frame),bool)
            for pn in self.candidates:
                g=available[available.pn.eq(pn)] if not available.empty else available
                valid=not g.empty and any((~g[f'{prefix}_{s}_fallback']).any() for s in SCALES)
                scores={s:float(log_score(g.y,g[f'{prefix}_{s}']).mean()) for s in SCALES} if valid else {}
                choice='calendar'
                reason='no_valid_internal_evaluation'
                if valid:
                    maximum=max(scores.values())
                    choice=next(s for s in SCALES if maximum-scores[s]<=1e-8)
                    reason='past_only_internal_log_score'
                mask=frame.pn.eq(pn).to_numpy()
                selected[mask]=choice
                pred[mask]=frame.loc[mask,f'{prefix}_{choice}']
                fb[mask]=frame.loc[mask,f'{prefix}_{choice}_fallback']
                self.selections.append(dict(variant=variant,origin=origin,pn=pn,model=prefix,
                    selected_scale=choice,reason=reason,internal_rows=len(g),
                    latest_internal_end=g.target_end.max() if not g.empty else pd.NaT,
                    **{f'log_{s}':scores.get(s,np.nan) for s in SCALES}))
            frame[f'{prefix}_selected']=pred
            frame[f'{prefix}_selected_scale']=selected
            frame[f'{prefix}_selected_fallback']=fb
        return frame

    def run_variant(self,variant):
        past=[]
        external=[]
        for origin in pd.date_range('2024-07-01','2025-12-01',freq='MS'):
            frame=self.forecast(origin,variant)
            if frame.empty:
                continue
            if origin>=pd.Timestamp('2025-01-01'):
                frame=self.select(frame,past,variant,origin)
                external.append(frame)
            past.append(frame)
        return pd.concat(external,ignore_index=True)


def cluster_means(frame,values):
    x=frame[['aircraft','origin','horizon']].copy()
    x['value']=np.asarray(values)
    return (x.groupby(['aircraft','origin','horizon']).value.mean()
            .groupby(['aircraft','origin']).mean().groupby('aircraft').mean())


def bootstrap_decision(frame,aircraft,candidates,reps=10000,aggregation='aircraft'):
    delta=log_score(frame.y,frame.w_selected)-log_score(frame.y,frame.baseline)
    rng=np.random.Generator(np.random.PCG64(SEED))
    draws=rng.integers(0,len(aircraft),size=(reps,len(aircraft)))
    columns={}
    point={}
    for pn in ('aggregate',*candidates):
        mask=np.ones(len(frame),bool) if pn=='aggregate' else frame.pn.eq(pn).to_numpy()
        means=cluster_means(frame[mask],delta[mask]).reindex(aircraft).to_numpy()
        if aggregation=='unit':
            x=frame.loc[mask,['aircraft']].copy()
            x['delta']=delta[mask]
            totals=x.groupby('aircraft').delta.agg(['sum','count']).reindex(aircraft).fillna(0.)
            counts=totals['count'].to_numpy()[draws].sum(axis=1)
            numerator=totals['sum'].to_numpy()[draws].sum(axis=1)
            columns[pn]=np.divide(numerator,counts,out=np.full(reps,np.nan),where=counts>0)
            point[pn]=float(np.mean(delta[mask])) if mask.any() else np.nan
            continue
        sampled=means[draws]
        valid=np.isfinite(sampled)
        counts=valid.sum(axis=1)
        boot=np.divide(np.nansum(sampled,axis=1),counts,
                       out=np.full(reps,np.nan),where=counts>0)
        columns[pn]=boot
        point[pn]=float(np.nanmean(means))
    rows=[]
    for pn,values in columns.items():
        finite=values[np.isfinite(values)]
        alpha=.05 if pn=='aggregate' else .05/len(candidates)
        lo,hi=np.quantile(finite,[.025,.975])
        simlo,simhi=np.quantile(finite,[alpha/2,1-alpha/2])
        rows.append(dict(pn=pn,delta_log=point[pn],ci_lo=lo,ci_hi=hi,
            simultaneous_lo=simlo,simultaneous_hi=simhi,missing_replicates=int((~np.isfinite(values)).sum())))
    summary=pd.DataFrame(rows)
    aggregate=summary[summary.pn.eq('aggregate')].iloc[0]
    passed=summary[summary.pn.ne('aggregate')&summary.simultaneous_lo.gt(0)].pn.tolist()
    outcome='favoravel' if aggregate.ci_lo>0 else 'mista' if passed else 'nula'
    return outcome,summary,pd.DataFrame(columns)


def metrics(frame):
    rows=[]
    calibration=[]
    names=(*MODELS,'w_selected','e_selected')
    for name in names:
        for pn in ('aggregate',*sorted(frame.pn.unique())):
            g=frame if pn=='aggregate' else frame[frame.pn.eq(pn)]
            log=cluster_means(g,log_score(g.y,g[name])).mean()
            brier=cluster_means(g,(g[name]-g.y)**2).mean()
            rows.append(dict(model=name,pn=pn,log_score=log,brier=brier,unit_predictions=len(g),
                fallback_share=float(g[name+'_fallback'].mean()) if name!='baseline' else 0.))
        ordered=frame.sort_values([name,'origin','horizon','spell_id'],kind='stable').copy()
        ordered['decil']=(np.arange(len(ordered))*10//len(ordered)+1).clip(1,10)
        for decile,g in ordered.groupby('decil'):
            expected=g[name].sum()
            calibration.append(dict(model=name,decil=decile,n=len(g),observed=int(g.y.sum()),
                expected=float(expected),observed_expected=float(g.y.sum()/expected) if expected>0 else np.nan))
    return pd.DataFrame(rows),pd.DataFrame(calibration)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preserve_initial_manifest(destination,archive,proposed):
    """Replays must not replace provenance of the original scientific run."""
    payload=(archive.read_bytes() if archive.exists() else
             (json.dumps(proposed,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    if not destination.exists() or destination.read_bytes()!=payload:
        destination.write_bytes(payload)


def main():
    OUT.mkdir(exist_ok=True)
    prereg=ROOT/'analysis'/'preregistro_A5.md'
    before=sha(prereg)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    prereg_revision=subprocess.check_output(['git','log','-1','--format=%H','--','analysis/preregistro_A5.md'],cwd=ROOT,text=True).strip()
    committed=subprocess.check_output(['git','show',f'{prereg_revision}:analysis/preregistro_A5.md'],cwd=ROOT)
    if committed.replace(b'\r\n',b'\n')!=prereg.read_bytes().replace(b'\r\n',b'\n'):
        raise ValueError('Preregistration differs from committed version')
    spells=pd.read_csv(DERIVED/'spells.csv',parse_dates=['att','rem'])
    flights=pd.read_csv(ANONYMISED/'hours_flown.csv')
    removals=pd.read_csv(DERIVED/'removals_clean.csv',parse_dates=['att','rem'])
    candidates=pd.read_csv(DERIVED/'k1_candidates.csv')
    candidates=sorted(candidates.loc[candidates.retained,'pn'])
    admin=pd.read_csv(DERIVED/'removal_label_audit.csv',parse_dates=['att','rem'])
    admin=admin[admin.audit_id.isin(ADMIN_IDS)]
    if len(admin)!=4:
        raise ValueError('Four administrative exclusions must be identified by full keys')
    tasks=load_omth()
    mapping=pd.read_csv(ROOT/'config'/'rotor_inspection_map.csv')
    engine=Evaluation(spells,flights,candidates,tasks,mapping,removals,admin)
    admin[KEYS+['audit_id']].to_csv(OUT/'administrative_exclusion_keys.csv',index=False)
    all_decisions=[]
    all_stats=[]
    all_calibration=[]
    all_boot=[]
    summaries=[]
    for variant in VARIANTS:
        print('A5 variant:',variant,flush=True)
        frame=engine.run_variant(variant)
        frame.to_csv(OUT/f'predictions_{variant}.csv',index=False)
        stats,calibration=metrics(frame)
        stats['variant'],calibration['variant']=variant,variant
        all_stats.append(stats)
        all_calibration.append(calibration)
        outcome,decisions,boot=bootstrap_decision(frame,engine.exposure.aircraft,candidates)
        decisions['variant']=variant
        all_decisions.append(decisions)
        boot['variant']=variant
        boot.index.name='replicate'
        all_boot.append(boot.reset_index())
        summaries.append(dict(variant=variant,outcome=outcome,unit_predictions=len(frame),
                              risk_spells=frame.spell_id.nunique(),aircraft=frame.aircraft.nunique()))
        counts=frame.groupby(['pn','aircraft','origin','horizon']).agg(
            risk_units=('spell_id','size'),observed=('y','sum'),
            weibull_expected=('w_selected','sum'),exponential_expected=('e_selected','sum'),
            baseline_expected=('baseline','sum')).reset_index()
        counts.to_csv(OUT/f'counts_{variant}.csv',index=False)
        coverage=frame.groupby(['origin','pn']).agg(
            predictions=('spell_id','size'),missing_hours_90d=('missing_hours_90d','max'),
            complete_takeoffs_share=('takeoffs_complete','mean'),
            weibull_fallback_share=('w_selected_fallback','mean'),
            exponential_fallback_share=('e_selected_fallback','mean')).reset_index()
        coverage.to_csv(OUT/f'coverage_{variant}.csv',index=False)
        complete=frame[frame.takeoffs_complete]
        if not complete.empty:
            complete_stats,_=metrics(complete)
            complete_stats.to_csv(OUT/f'complete_cases_metrics_{variant}.csv',index=False)
        print('Completed',variant,'K2',outcome,flush=True)
    fits=pd.DataFrame(engine.fits)
    selection=pd.DataFrame(engine.selections)
    fits.to_csv(OUT/'fits.csv',index=False)
    selection.to_csv(OUT/'scale_selection.csv',index=False)
    pd.concat(all_decisions,ignore_index=True).to_csv(OUT/'k2_intervals.csv',index=False)
    pd.concat(all_stats,ignore_index=True).to_csv(OUT/'metrics.csv',index=False)
    pd.concat(all_calibration,ignore_index=True).to_csv(OUT/'calibration.csv',index=False)
    pd.concat(all_boot,ignore_index=True).to_csv(OUT/'bootstrap_replicates.csv',index=False)
    summary=pd.DataFrame(summaries)
    summary.to_csv(OUT/'decision.csv',index=False)
    inputs=[prereg,ROOT/'analysis'/'emenda_A5_001.md',ANONYMISED/'hours_flown.csv',
        DERIVED/'spells.csv',DERIVED/'removals_clean.csv',ANONYMISED/'OMTH_tasks.csv',
        DERIVED/'k1_candidates.csv',ROOT/'config'/'rotor_inspection_map.csv',
        DERIVED/'removal_label_audit.csv',DERIVED/'adjudication_status.csv',
        DERIVED/'extended_review_results.csv',ROOT/'analysis'/'a5_models.py',ROOT/'analysis'/'a5_validation.py']
    manifest=dict(preregistration_sha256=before,preregistration_git_revision=prereg_revision,
        execution_git_revision=revision,seed=SEED,bootstrap_reps=10000,
        versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__),
        inputs={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in inputs})
    preserve_initial_manifest(OUT/'manifest.json',ROOT/'analysis'/'audit'/'a5_initial_manifest.json',manifest)
    if sha(prereg)!=before:
        raise ValueError('Preregistration was modified')
    principal=all_decisions[0].round(7)
    report=f'''# A5 — validação preditiva temporal e decisão K2

Pré-registro A5_v1 preservado, revisão {prereg_revision}; emenda A5_001 anterior
à execução. Coorte principal dos {len(candidates)} candidatos K1, com seleção
temporal interna, riscos concorrentes, bootstrap de aeronaves e seis variantes.

## Decisão principal e sensibilidades

{summary.to_markdown(index=False)}

## Diferenças pareadas do log score, principal

{principal.to_markdown(index=False)}

Maior é melhor. IC agregado 95%; por P/N também intervalos simultâneos Bonferroni.
K2 usa somente o principal; sensibilidades não substituem seu critério. K1 foi
selecionado na janela completa: K2 é condicionado a essa seleção retrospectiva.
Não constitui validação externa nem demonstra ganho económico do ciclo dinâmico.
Comparação Weibull–exponencial, Brier, calibração, cobertura e fallbacks disponíveis
nas tabelas de métricas; menor Brier é melhor. A interpretação física da vida e
a transportabilidade para políticas alternativas permanecem limitações.

Artefatos em `data/derived/a5/`: predições individuais, contagens, cobertura,
casos completos, ajustes, seleção de escala, métricas, calibração, bootstrap,
sensibilidades e manifesto de versões/hashes. Nenhum texto livre foi exportado.
'''
    (ROOT/'analysis'/'a5_report.md').write_text(report,encoding='utf-8')
    print(summary.to_string(index=False),flush=True)


if __name__=='__main__':
    main()
