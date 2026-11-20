"""Recover computational evidence only; never load evaluation outcomes."""
import collections
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

from a9_environment import historical_calendars
from a9_warmup import SharedWarmup
from a16_generator import START

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/derived/a9/decomposition'
PILOT = ROOT / 'data/derived/a9/pilot_optimised'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    stats = collections.defaultdict(lambda: dict(pulses=0, reserved=0, pending=set()))
    stage, policy = 'warmup_initial_fit', None
    for line in (PILOT / 'stdout.log').read_text(encoding='utf-8').splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get('stage') == 'initial_fit':
            stage = 'warmup_initial_fit'
        if record.get('stage') == 'policy':
            policy = record['policy']
            stage = f"{policy}:{record['month']}"
        if record.get('stage') == 'P1_calibration_parallel' and policy is None:
            stage = 'initial_P1'
        item = stats[stage]
        if record.get('stage') == 'P1_calibration_parallel':
            item['pulses'] += 1
            item['reserved'] = max(item['reserved'], record['estimated_calibration_bytes'])
            item['pending'].update(record['pending_pns'])
    return stats


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    interruption = json.loads((PILOT / 'authorised_interruption.json').read_text())
    state = json.loads((PILOT / 'state_before_second_authorised_interruption.json').read_text())
    prior_path = ROOT / 'data/derived/a9/optimisation/prior_costs.json'
    prior = json.loads(prior_path.read_text())
    stats = collect()
    total = interruption['wall_seconds_since_pilot_started']
    lower_sum = sum(max(0, s['pulses'] - 1) * 5 for s in stats.values())
    rows = []
    stages = [('warmup_initial_fit', 'Aquecimento + ajuste inicial', 'concluído'),
              ('initial_P1', 'Calibração inicial P1', 'concluída')]
    for policy in ('P0', 'P1', 'P2', 'P3', 'P2_fixed'):
        assert all(f'{policy}:{month}' in stats for month in range(24))
        stages.append((policy, ('P2_noreest (P2_fixed)' if policy == 'P2_fixed' else policy) + ' — 24 meses', 'concluída'))
    for month in range(24):
        label = f'P2_age {2024 + month // 12}-{1 + month % 12:02d}'
        stages.append((f'P2_age:{month}', label,
                       'concluído' if month < 5 else 'interrompido' if month == 5 else 'não iniciado'))
    for key, label, status in stages:
        item = stats.get(key, dict(pulses=0, reserved=0, pending=set()))
        lower = max(0, item['pulses'] - 1) * 5
        reached = status != 'não iniciado'
        rows.append(dict(stage=key, label=label, status=status, wall_seconds_exact=None,
                         wall_seconds_lower_bound=lower if reached else None,
                         wall_seconds_upper_bound=total - lower_sum + lower if reached else None,
                         peak_rss_bytes_measured=None,
                         max_reserved_bytes_estimate=item['reserved'] or None,
                         calibration_pulses=item['pulses'],
                         thresholds_evaluated=None, phases_evaluated=None))
    shared = SharedWarmup(ROOT / 'data/derived/a9/warmup/replicas/pilot_amplified_0000')
    spells, flights = shared.for_policy('P0')
    domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
    contexts, _ = historical_calendars(spells, flights, pd.read_csv(ROOT / 'data/derived/stoppages.csv'), domain, START)
    pns = []
    for pn, context in sorted(contexts.items()):
        informative = [c for c in context if c['visits'] and sum(c['daily']) > 0]
        pns.append(dict(pn=pn, contexts=len(context), informative_contexts=len(informative),
                        declared_phase_states_grid1=sum(len(c['daily']) for c in informative),
                        declared_phase_states_grid2=sum(len(c['daily']) * 2 for c in informative),
                        declared_phase_states_grid4=sum(len(c['daily']) * 4 for c in informative),
                        actual_threshold_count=None, actual_phase_count=None))
    templates, mapping = {}, []
    for pn, context in sorted(contexts.items()):
        aircraft = sorted(spells.loc[spells['Part #'].eq(pn) & spells.att.lt(START), 'Aircraft #'].unique())
        assert len(aircraft) == len(context)
        for ac, item in zip(aircraft, context):
            if not item['visits'] or sum(item['daily']) == 0:
                continue
            import numpy as np
            signature = hashlib.sha256(np.asarray(item['daily'], dtype='<f8').tobytes() +
                                       np.asarray(item['visits'], dtype='<i8').tobytes()).hexdigest()
            templates.setdefault(signature, len(templates))
            mapping.append(dict(pn=pn, aircraft=ac.removesuffix('-AUX'), template=templates[signature],
                                calendar_clock_sha256=signature))
    inventory = dict(mapping=mapping, unique_templates=len(templates), informative_pn_aircraft_pairs=len(mapping),
                     nodes_per_template_r=1296, validation_points_per_template_r=326,
                     total_exact_nodes=len(templates)*3*1296, total_exact_validation=len(templates)*3*326)
    (OUT / 'surface_planning_inventory.json').write_text(json.dumps(inventory, indent=2)+'\n', encoding='utf-8')
    known = prior['known_recorded_seconds'] + total
    ledger = dict(budget_hours_total=120, prior_ledger=str(prior_path.relative_to(ROOT)).replace('\\', '/'),
                  prior_ledger_sha256=digest(prior_path), prior_known_recorded_seconds=prior['known_recorded_seconds'],
                  additional_events=[dict(source='data/derived/a9/pilot_optimised/authorised_interruption.json',
                                          sha256=digest(PILOT / 'authorised_interruption.json'), seconds=total)],
                  known_recorded_seconds=known, remaining_seconds_upper_bound=max(0, 432000-known),
                  gaps=[*prior['gaps'], 'Decomposition/planning work was not separately wall-clocked; no zero-cost assumption'], unknown_costs_not_imputed=True,
                  excludes_cpu_seconds_from_wall_sum=True)
    paths = [PILOT / n for n in ('stdout.log', 'stderr.log', 'configuration.json', 'authorised_interruption.json',
                                 'state_before_second_authorised_interruption.json', 'replica_00.json')]
    paths += [Path(__file__), ROOT / 'analysis/a9_parallel.py', ROOT / 'analysis/a9_monitor.py']
    snapshot = sum(p['rss'] for p in interruption['processes'])
    report = dict(configuration_sha256=interruption['configuration_sha256'], wall_seconds=total,
                  calibration_wall_seconds_lower_bound=lower_sum,
                  unallocated_wall_seconds_upper_bound=total-lower_sum,
                  aggregate_peak_rss_bytes_sampled=state['aggregate_peak_rss_bytes_sampled'],
                  rss_bytes_snapshot_P2_age_2024_06=snapshot,
                  cpu_seconds_sampled_lower_bound=interruption['previous_monitor_cpu_seconds_lower_bound'],
                  stages=rows, pn_counts=pns, outcomes_inspected=False,
                  exact_stage_telemetry_available=False,
                  sources={str(p.relative_to(ROOT)).replace('\\', '/'):digest(p) for p in paths})
    for name, data in [('decomposition.json', report), ('accumulated_costs.json', ledger)]:
        (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    for name, data in [('stages.csv', rows), ('pn_counts.csv', pns)]:
        with (OUT / name).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    lines = ['# Decomposição computacional da réplica parcial A9', '',
             '15/11/2026. Entrega anterior à preparação da emenda 014. Nenhum desfecho aberto.', '',
             f'PID 34396 e seis filhos encerrados por autorização expressa às {interruption["recorded_utc"]}.',
             'Estado, logs e checkpoint parcial preservados; réplica 0 excluída de R, sem conclusão forçada.', '',
             f'Tempo de parede medido: **{total:.6f} s ({total/3600:.6f} h)**. CPU amostrada acumulada: '
             f'**≥{report["cpu_seconds_sampled_lower_bound"]:.6f} s**; CPU paralela não é somada ao orçamento de parede.',
             f'Pico agregado de RSS amostrado: **{report["aggregate_peak_rss_bytes_sampled"]} bytes '
             f'({report["aggregate_peak_rss_bytes_sampled"]/2**30:.3f} GiB)**; não atribuível a uma etapa.',
             f'RSS agregado no instante da interrupção, em junho/P2_age: **{snapshot} bytes ({snapshot/2**30:.3f} GiB)**. '
             'É uma observação pontual, não o pico da etapa.', '',
             '## Limites de recuperação', '',
             'stdout.log contém eventos sem relógio; state.json foi sobrescrito. O monitor conservava somente '
             'máximos globais. Tempos dos jobs, contagens de breakpoints e diagnósticos completos ficaram em RAM '
             'até o final das seis políticas e não foram persistidos antes da interrupção. Não existe perfil '
             'por etapa recuperável. NA significa não registrado; nunca significa zero.', '',
             'Cada chamada de calibração emite pulsos separados por pelo menos 5 s (a9_parallel.py). '
             'N pulsos certificam ≥5(N−1) s, não uma duração exata. O limite superior de cada etapa alcançada '
             'é o total menos os limites inferiores das outras etapas. Os limites superiores não são aditivos. '
             'Os limites dos meses incluem ajuste e simulação, enquanto seus limites inferiores provêm apenas '
             'da calibração. Não se estima tempo multiplicando pulsos por uma cadência suposta exata.', '',
             f'Calibrações consumiram **≥{lower_sum:.0f} s ({lower_sum/3600:.4f} h)**. '
             f'O restante não atribuível é **≤{total-lower_sum:.6f} s**; inclui atrasos dos pulsos e todas as outras operações.', '',
             '## Etapas solicitadas', '',
             '| Etapa | Estado | Parede: limite inferior–superior (s) | Pico RSS medido por etapa | Máxima reserva estimada (GiB) |',
             '|---|---|---:|---|---:|']
    for row in rows:
        interval = 'NA' if row['wall_seconds_lower_bound'] is None else f'{row["wall_seconds_lower_bound"]:.0f}–{row["wall_seconds_upper_bound"]:.3f}'
        reserve = 'NA' if not row['max_reserved_bytes_estimate'] else f'{row["max_reserved_bytes_estimate"]/2**30:.3f}'
        lines.append(f'| {row["label"]} | {row["status"]} | {interval} | NA | {reserve} |')
    lines += ['', 'Reserva é previsão de matrizes dos jobs pendentes, não RSS observado nem máximo real. '
              'Aquecimento reutilizou a coorte persistida; sua geração anterior não foi repetida. '
              'A duração exata de carga/ajuste não foi registrada. P2_noreest corresponde a P2_fixed no código.', '',
              '## Limiares e fases por P/N', '',
              'Contagens efetivamente avaliadas: **NA para todos os P/N, em todas as chamadas**. '
              'As colunas seguintes reconstroem somente o tamanho declarado das matrizes de fases '
              '(soma dos calendários informativos), usando exclusivamente a coorte auxiliar já congelada. '
              'Não são contagens de fases realmente visitadas, nem de limiares. Cada calendário tem '
              '365/730/1460 fases nas grades 1/2/4; a grade 4 é condicional ao refinamento. '
              'β≤1 usa o ramo sem prevenção, sem enumeração de limiares. Não se pode inferir a grade '
              'atingida nem a quantidade de breakpoints de uma lista de P/N pendentes.', '',
              '| P/N | Contextos informativos/total | Fases declaradas grade 1 | grade 2 | grade 4 | Limiares reais | Fases reais |',
              '|---|---:|---:|---:|---:|---|---|']
    for p in pns:
        lines.append(f'| {p["pn"]} | {p["informative_contexts"]}/{p["contexts"]} | {p["declared_phase_states_grid1"]} | '
                     f'{p["declared_phase_states_grid2"]} | {p["declared_phase_states_grid4"]} | NA | NA |')
    lines += ['', '## Ledger e disponibilidade', '',
              f'Anterior congelado: {prior["known_recorded_seconds"]:.6f} s. Acrescentado uma única vez: {total:.6f} s. '
              f'Acumulado conhecido: **{known:.6f} s ({known/3600:.6f} h)**. '
              f'Restante: **≤{ledger["remaining_seconds_upper_bound"]/3600:.6f} h**. '
              'Lacunas anteriores continuam explícitas; não há reinício do orçamento.', '',
              'Arquivos: data/derived/a9/decomposition/{decomposition.json,stages.csv,pn_counts.csv,accumulated_costs.json}. '
              'decomposition.json contém hashes dos registros e do reconstrutor. O ledger anterior foi preservado sem alteração.', '']
    (ROOT / 'analysis/a9_partial_time_decomposition.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(dict(wall_seconds=total, calibration_lower_seconds=lower_sum,
                          residual_upper_seconds=total-lower_sum, known_seconds=known,
                          remaining_hours_upper=ledger['remaining_seconds_upper_bound']/3600,
                          threshold_seconds_per_replica_upper=ledger['remaining_seconds_upper_bound']/(72*1.5*200)), indent=2))


if __name__ == '__main__':
    run()
