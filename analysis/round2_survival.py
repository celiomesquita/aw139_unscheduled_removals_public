"""T2: operational inspection intervals and prespecified K1 decision."""
import numpy as np
import pandas as pd

from feasibility import DERIVED, ROOT, load_omth
from inspection_censoring import fit_mixed

MAP = ROOT/'config'/'rotor_inspection_map.csv'


def bounds(spells, tasks, mapping, clock, generic_fh):
    rows=[]
    for idx,r in spells.iterrows():
        upper=float(r.fh_rem-r.fh_att)
        mapped=bool(r.event and r['Part #'] in set(mapping.pn))
        lower=upper
        reason='exact_outside_mapped_ata62' if not mapped else 'censored'
        task_ref=''
        date=pd.NaT
        if mapped:
            relevant=tasks[(tasks['Aircraft #']==r['Aircraft #']) &
                tasks['Task #'].isin(mapping.loc[mapping.pn.eq(r['Part #']),'task']) &
                tasks.d.lt(r.rem) & tasks.d.ge(r.att)].sort_values(['d','Task #'])
            if relevant.empty:
                lower=0.
                reason='no_previous_inspection_since_installation'
            else:
                last=relevant.iloc[-1]
                date=last.d
                task_ref=last['Task #']
                lower=max(0.,float(clock.at[date,r['Aircraft #']]-r.fh_att))
                reason='last_mapped_head_inspection'
            if upper<=lower:
                # Zero-width exposure cannot support an interval probability.
                # Preserve the event as exact; never move its lower bound by epsilon.
                reason='zero_width_map_interval_kept_exact'
                lower=upper
        rows.append(dict(spell_id=idx,pn=r['Part #'],aircraft=r['Aircraft #'],
            installation=r.att,removal=r.rem,event=int(r.event),upper_fh=upper,
            map_lower_fh=lower,map_interval=bool(mapped and 0<=lower<upper),
            generic_lower_fh=max(0.,upper-generic_fh) if mapped else upper,
            generic_interval=bool(mapped and upper>0),map_reason=reason,
            last_inspection_date=date,last_inspection_task=task_ref))
    return pd.DataFrame(rows)


def decide_k1(fits):
    rows=[]
    for pn,g in fits.groupby('pn'):
        exact=g[g.version.eq('exact')].iloc[0]
        mapped=g[g.version.eq('mapped')].iloc[0]
        approved=bool(exact.converged and mapped.converged and
                      exact.beta_lo>1 and mapped.beta_lo>1)
        rows.append(dict(pn=pn,retained=approved,exact_beta_lo=exact.beta_lo,
                         mapped_beta_lo=mapped.beta_lo))
    return pd.DataFrame(rows)


def main():
    sp=pd.read_csv(DERIVED/'spells.csv',parse_dates=['att','rem'])
    candidates=pd.read_csv(DERIVED/'weibull_by_pn.csv')
    candidates=candidates[candidates.regime.eq('wear-out')]
    sp=sp[sp.source.isin(['in_window_removed','in_window_censored']) &
          sp['Part #'].isin(candidates.pn)].copy()
    clock=pd.read_csv(DERIVED/'aircraft_fh_daily.csv',index_col=0,parse_dates=True)
    mapping=pd.read_csv(MAP)
    recurrence=pd.read_csv(DERIVED/'recurrent_tasks.csv').set_index('Task #')
    if not mapping.task.isin(recurrence.index).all() or not recurrence.loc[mapping.task,'periodic'].all():
        raise ValueError('Map must use recurrent periodic task codes')
    generic=float(recurrence.loc[sorted(mapping.task.unique()),'med_fh'].median())
    intervals=bounds(sp,load_omth(),mapping,clock,generic)
    intervals.to_csv(DERIVED/'round2_inspection_bounds.csv',index=False)
    rows=[]
    for pn,g in intervals.groupby('pn'):
        valid=g.upper_fh.gt(0)
        kept=g[valid]
        for version in ('exact','mapped','generic'):
            mask=(np.zeros(len(kept),bool) if version=='exact' else
                  kept['map_interval' if version=='mapped' else 'generic_interval'].to_numpy())
            lower=(kept.upper_fh.to_numpy() if version=='exact' else
                   kept['map_lower_fh' if version=='mapped' else 'generic_lower_fh'].to_numpy())
            fit=fit_mixed(lower,kept.upper_fh,kept.event,mask)
            rows.append(dict(pn=pn,ata=int(candidates.set_index('pn').at[pn,'ata']),
                version=version,spells=len(kept),events=int(kept.event.sum()),
                intervals=int(mask.sum()),zero_exposure_excluded=int((~valid).sum()),**fit))
    fits=pd.DataFrame(rows)
    decision=decide_k1(fits)
    fits.to_csv(DERIVED/'round2_weibull_fits.csv',index=False)
    decision.to_csv(DERIVED/'k1_candidates.csv',index=False)
    retained=int(decision.retained.sum())
    outcome='favorável' if retained>=5 else 'desfavorável'
    report=f'''# T2 — A3 ampliada e decisão K1

Desfecho: remoção não programada registrada (T1), não falha física confirmada.
Regra fixada em `tarefas_codex.md`: IC de beta acima de 1 na versão exata e
na versão intervalar com mapa; K1 favorável com pelo menos cinco P/N retidos.

## Mapa e observação

`config/rotor_inspection_map.csv` fixa tarefa/P/N e motivo em códigos. Seleciona
tarefas periódicas específicas de amortecedor e tesouras/cabeça do rotor principal
de `recurrent_tasks.csv`. Não presume que inspeções genéricas de célula observem
esse conjunto. O mapa amplo representa uma aproximação operacional compartilhada
entre componentes da cabeça; não comprova detectabilidade de cada modo físico.
Inclui os seis candidatos ATA 62, inclusive parafuso e terminal. Usa a última
execução anterior à remoção na mesma aeronave, independentemente do documento,
sem ultrapassar a instalação. Sem execução anterior na instalação: limite zero.
Exposição FH nula: exclusão idêntica nas três versões, quantificada na tabela.
Última inspeção com mesma exposição FH da remoção: intervalo não identificável,
evento conservado como exato na versão com mapa, sem inventar exposição positiva.
Genérica: (max(0, idade−{generic:.2f} FH), idade].
Fora do ATA 62 (incluindo tesoura de cauda ATA 64), mantém eventos exatos porque
o mapa de cabeça do rotor principal não se aplica. Censuras conservam a exposição
integral. Coorte principal, entrada em idade zero; sem extrapolação pré-2024.

## Ajustes

{fits.round(4).to_markdown(index=False)}

IC 95% Wald em log beta, ainda sem correção por dependência entre trechos da
mesma aeronave. Bootstrap por aeronave não executado nesta rodada (opcional).
Não comparar AIC entre versões com observações exatas e intervalares.

## Decisão

**K1 {outcome}: {retained} de {len(decision)} P/N retidos.**

{decision.round(4).to_markdown(index=False)}

A decisão é sobre padrão de idade no processo de remoção, sob o mapa operacional
assumido. Não confirma desgaste físico nem eficácia de política. K2 ainda não
avaliado; sobrevivência e seleção temporal de escala serão examinadas em A5.
'''
    (ROOT/'analysis'/'round2_survival_report.md').write_text(report,encoding='utf-8')
    print(f'K1 {outcome}: {retained}/{len(decision)}')
    print(decision.to_string(index=False))


if __name__=='__main__':
    main()
