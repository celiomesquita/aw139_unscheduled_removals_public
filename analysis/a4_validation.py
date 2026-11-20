"""A4_v1 adapter: mechanism families, fixed scales and reused A5 forecasting."""
import hashlib
import json
import subprocess

import numpy as np
import pandas as pd

from feasibility import ROOT,DERIVED,ANONYMISED,load_omth
from a5_models import fit_survival
from a5_validation import Evaluation,ADMIN_IDS,KEYS,metrics,bootstrap_decision,sha
from a4_models import fit_hierarchy

OUT=DERIVED/'a4'
VARIANTS=('principal','realized_fh','wheels_takeoffs','imputed_takeoffs',
          'inspection_intervals','provenance','no_admin','expanded_bounds')


def scale_map(candidates):
    rows=[]
    for r in candidates.itertuples():
        ata=int(r.ata)//100
        family='rotor' if ata in (62,64) else 'wheels' if ata==32 else 'vests' if ata==25 else None
        if family is None:raise ValueError('Unmapped mechanism')
        rows.append(dict(pn=r.pn,ata=ata,family=family,scale='calendar' if family=='vests' else 'FH'))
    result=pd.DataFrame(rows).sort_values('pn')
    if result.pn.duplicated().any() or result.family.value_counts().to_dict()!={'rotor':7,'wheels':2,'vests':2}:
        raise ValueError('A4_v1 requires eleven PN in mechanism families 7/2/2')
    return result


class HierarchicalEvaluation(Evaluation):
    def __init__(self,*args,domain,**kwargs):
        super().__init__(*args,**kwargs)
        self.domain=domain.set_index('pn')
        self.hyper=[];self.effects=[]

    def prepare(self,origin,variant):
        # Reuse the complete training cut, nuisance intensities and exposure
        # rules. Individual fits remain reference diagnostics, never selection.
        train,risk,clock,lam,nu,reference=super().prepare(origin,variant)
        records={};families={};scales={}
        for pn in self.candidates:
            g=train[train.pn.eq(pn)]
            fam=self.domain.at[pn,'family']
            scale=self.domain.at[pn,'scale']
            if variant in ('wheels_takeoffs','imputed_takeoffs') and fam=='wheels':scale='takeoffs'
            upper=self.exposure.ages(g,g.end,clock,scale)
            valid=np.isfinite(upper)&(upper>0)
            if scale=='takeoffs':valid &= ~self.exposure.incomplete(g,g.end,clock,'missing_cycles')
            lower=upper.copy();iv=np.zeros(len(g),bool)
            if variant=='inspection_intervals' and pn in set(self.mapping.pn):
                for j,(_,r) in enumerate(g.iterrows()):
                    if not r.train_event:continue
                    tasks=self.tasks[(self.tasks['Aircraft #']==r['Aircraft #']) &
                        self.tasks['Task #'].isin(self.mapping.loc[self.mapping.pn.eq(pn),'task']) &
                        self.tasks.d.ge(r.att)&self.tasks.d.lt(r.end)&self.tasks.d.lt(origin)]
                    last=tasks.d.max() if len(tasks) else r.att
                    lower[j]=self.exposure.ages(g.iloc[[j]],[last],clock,scale)[0]
                    iv[j]=0<=lower[j]<upper[j]
            records[pn]=dict(t=upper[valid],d=g.train_event.to_numpy()[valid],
                lower=lower[valid],interval=iv[valid],zero_event_excluded=int((g.train_event&~valid).sum()))
            families[pn]=fam;scales[pn]=scale
        eligible={fam:sum(records[p]['d'].sum() for p in records if families[p]==fam)>=5
                  for fam in set(families.values())}
        data={p:r for p,r in records.items() if eligible[families[p]]}
        fitted={key:dict(converged=False) for key in reference}
        for prefix in ('w','e'):
            if data:
                estimates,hyper=fit_hierarchy(data,{p:families[p] for p in data},prefix,variant=='expanded_bounds')
            else:estimates,hyper={},dict(converged=False,attempts=0,evaluations=0)
            self.hyper.append(dict(variant=variant,origin=origin,model=prefix,**hyper))
            for pn in self.candidates:
                effect=estimates.get(pn,dict(converged=False,beta=np.nan,eta=np.nan,
                    n=len(records[pn]['t']),events=int(records[pn]['d'].sum()),intervals=0))
                effect['fit_reason']=('hierarchical_marginal_fit' if effect['converged'] else
                    'family_fewer_than_5_events' if not eligible[families[pn]] else 'marginal_or_conditional_failure')
                fitted[(pn,prefix,scales[pn])]=effect
                self.effects.append(dict(variant=variant,origin=origin,pn=pn,family=families[pn],
                    scale=scales[pn],model=prefix,**effect))
        return train,risk,clock,lam,nu,fitted

    def select(self,frame,past,variant,origin):
        for prefix in ('w','e'):
            frame[prefix+'_selected']=np.nan
            frame[prefix+'_selected_fallback']=True
            for pn in self.candidates:
                fam=self.domain.at[pn,'family'];scale=self.domain.at[pn,'scale']
                if variant in ('wheels_takeoffs','imputed_takeoffs') and fam=='wheels':scale='takeoffs'
                mask=frame.pn.eq(pn)
                frame.loc[mask,prefix+'_selected']=frame.loc[mask,prefix+'_'+scale]
                frame.loc[mask,prefix+'_selected_fallback']=frame.loc[mask,prefix+'_'+scale+'_fallback']
                frame.loc[mask,prefix+'_selected_scale']=scale
        return frame

    def run_variant(self,variant):
        frames=[]
        for origin in pd.date_range('2025-01-01','2025-12-01',freq='MS'):
            print(variant,origin.strftime('%Y-%m'),flush=True)
            f=self.forecast(origin,variant)
            if len(f):frames.append(self.select(f,[],variant,origin))
        return pd.concat(frames,ignore_index=True)


def main():
    OUT.mkdir(exist_ok=True)
    prereg=ROOT/'analysis'/'preregistro_A4.md'
    digest=sha(prereg)
    revision=subprocess.check_output(['git','log','-1','--format=%H','--','analysis/preregistro_A4.md'],cwd=ROOT,text=True).strip()
    original=subprocess.check_output(['git','show',revision+':analysis/preregistro_A4.md'],cwd=ROOT)
    if original.replace(b'\r\n',b'\n')!=prereg.read_bytes().replace(b'\r\n',b'\n'):
        raise ValueError('A4 preregistration is not the committed version')
    candidates=pd.read_csv(DERIVED/'weibull_by_pn.csv')
    keep=pd.read_csv(DERIVED/'k1_candidates.csv')
    candidates=candidates[candidates.pn.isin(keep.loc[keep.retained,'pn'])]
    domain=scale_map(candidates)
    domain.to_csv(ROOT/'config'/'a4_scale_map.csv',index=False)
    spells=pd.read_csv(DERIVED/'spells.csv',parse_dates=['att','rem'])
    removals=pd.read_csv(DERIVED/'removals_clean.csv',parse_dates=['att','rem'])
    flights=pd.read_csv(ANONYMISED/'hours_flown.csv')
    admin=pd.read_csv(DERIVED/'removal_label_audit.csv',parse_dates=['att','rem'])
    admin=admin[admin.audit_id.isin(ADMIN_IDS)]
    engine=HierarchicalEvaluation(spells,flights,domain.pn.tolist(),load_omth(),
        pd.read_csv(ROOT/'config'/'rotor_inspection_map.csv'),removals,admin,domain=domain)
    intervals=[];boots=[];scores=[];calibrations=[];decisions=[]
    for variant in VARIANTS:
        frame=engine.run_variant(variant)
        frame.to_csv(OUT/('predictions_'+variant+'.csv'),index=False)
        m,c=metrics(frame)
        m=m[m.model.isin(['w_selected','e_selected','baseline'])]
        c=c[c.model.isin(['w_selected','e_selected','baseline'])]
        m['variant']=variant;c['variant']=variant
        scores.append(m);calibrations.append(c)
        counts=frame.groupby(['pn','aircraft','origin','horizon']).agg(
            risk_units=('spell_id','size'),observed=('y','sum'),hW_expected=('w_selected','sum'),
            hE_expected=('e_selected','sum'),baseline_expected=('baseline','sum')).reset_index()
        counts.to_csv(OUT/('counts_'+variant+'.csv'),index=False)
        for aggregation in (('aircraft','unit') if variant=='principal' else ('aircraft',)):
            for criterion in ('K2-A4','K2-idade'):
                paired=frame.copy()
                if criterion=='K2-idade':paired['baseline']=paired.e_selected
                outcome,ci,boot=bootstrap_decision(paired,engine.exposure.aircraft,engine.candidates,
                                                   aggregation=aggregation)
                for obj in (ci,boot):
                    obj['variant']=variant;obj['aggregation']=aggregation;obj['criterion']=criterion
                intervals.append(ci);boots.append(boot.reset_index(names='replicate'))
                decisions.append(dict(variant=variant,aggregation=aggregation,criterion=criterion,outcome=outcome,
                    predictions=len(frame),risk_spells=frame.spell_id.nunique(),aircraft=frame.aircraft.nunique()))
        pd.DataFrame(engine.hyper).to_csv(OUT/'hyperparameters.csv',index=False)
        pd.DataFrame(engine.effects).to_csv(OUT/'effects.csv',index=False)
        pd.DataFrame(decisions).to_csv(OUT/'decision.csv',index=False)
    pd.concat(intervals,ignore_index=True).to_csv(OUT/'intervals.csv',index=False)
    pd.concat(boots,ignore_index=True).to_csv(OUT/'bootstrap.csv',index=False)
    pd.concat(scores,ignore_index=True).to_csv(OUT/'metrics.csv',index=False)
    pd.concat(calibrations,ignore_index=True).to_csv(OUT/'calibration.csv',index=False)
    pd.DataFrame(engine.fits).to_csv(OUT/'individual_reference_fits.csv',index=False)
    paths=[prereg,ROOT/'analysis'/'emenda_A4_001.md',ROOT/'analysis'/'emenda_A4_002.md',ROOT/'analysis'/'a4_models.py',
        ROOT/'analysis'/'a4_validation.py',ROOT/'analysis'/'a5_models.py',ROOT/'analysis'/'a5_validation.py',
        DERIVED/'spells.csv',DERIVED/'removals_clean.csv',DERIVED/'k1_candidates.csv',
        ANONYMISED/'hours_flown.csv',ANONYMISED/'OMTH_tasks.csv',ROOT/'config'/'a4_scale_map.csv']
    manifest=dict(preregistration_git_revision=revision,preregistration_sha256=digest,
        seed=20261112,bootstrap_reps=10000,inputs={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    if sha(prereg)!=digest:raise ValueError('A4 preregistration changed')
    decision=pd.DataFrame(decisions)
    principal=pd.concat(intervals,ignore_index=True)
    principal=principal[principal.variant.eq('principal')&principal.aggregation.eq('aircraft')]
    primary=decision[decision.variant.eq('principal')&decision.aggregation.eq('aircraft')].set_index('criterion').outcome
    supported={k:set(principal.loc[principal.criterion.eq(k)&principal.pn.ne('aggregate')&
        principal.simultaneous_lo.gt(0),'pn']) for k in ('K2-A4','K2-idade')}
    allowed=set()
    if primary['K2-A4']=='favoravel' and primary['K2-idade']=='favoravel':allowed=set(engine.candidates)
    elif primary['K2-A4']=='favoravel' and primary['K2-idade']=='mista':allowed=supported['K2-idade']
    elif primary['K2-A4']=='mista' and primary['K2-idade'] in ('favoravel','mista'):
        allowed=supported['K2-A4']&supported['K2-idade']
    pd.DataFrame([dict(pn=p,candidate_for_future_A7=p in allowed) for p in engine.candidates]).to_csv(
        OUT/'future_policy_scope.csv',index=False)
    report=f'''# A4 — execução pós-hoc segundo A4_v1

Pré-registro preservado, revisão {revision}; emenda A4_001 anterior à execução.
Famílias por mecanismo 7/2/2; log beta global; log eta por família.
Reutiliza exposição, risco concorrente, previsões, métricas e bootstrap de A5.
Escalas fixadas pelo domínio, sem seleção de escala pelos alvos de A4.

## Decisões e sensibilidades

{decision.to_markdown(index=False)}

## Principal, agregação por aeronave

{principal.round(7).to_markdown(index=False)}

Maior log score é melhor. As duas comparações são obrigatórias; a média simples
por unidade é apenas sensibilidade. K2 nulo de A5 permanece preservado.
Nenhuma otimização A7 foi executada. T7 termina aqui, qualquer que seja o resultado.
O subconjunto elegível segundo as duas decisões está em future_policy_scope.csv;
nenhum caso é aprovado por uma sensibilidade isolada.
Hiperparâmetros, modos condicionais, falhas, fronteiras e fallbacks constam nas
tabelas de data/derived/a4/. Nenhum texto livre operacional foi exportado.
'''
    (ROOT/'analysis'/'a4_report.md').write_text(report,encoding='utf-8')
    print(decision.to_string(index=False))


if __name__=='__main__':main()
