"""Check preregistered prerequisites without generating A9 policy outcomes."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from a16_generator import ROOT, committed_protocol, sha
from round5_execution import amendment006, atomic_json, check_historical

OUT = ROOT / 'data/derived/a9/preflight'


def preventive_mh(domain, summary, parameters):
    """Use only T4 single-removal documents; never substitute equal sharing."""
    records = []
    for pn in sorted(domain.pn):
        selected = summary[(summary.pn == pn) &
                           (summary.aggregation == 'row_sum') &
                           (summary.cohort == 'single_document')]
        if len(selected) != 1:
            raise ValueError('Expected one T4 single-document summary: ' + pn)
        row = selected.iloc[0]
        central = float(row['median'])
        available = int(row.n_observed) > 0 and np.isfinite(central) and central > 0
        configured = parameters[parameters.parametro == 'mh_row_sum_' + pn]
        if available:
            if len(configured) != 1:
                raise ValueError('Missing configured T4 coefficient: ' + pn)
            actual = float(configured.iloc[0].valor_central)
            if actual != central:
                raise ValueError('Config differs from T4: ' + pn)
        records.append(dict(pn=pn, documents=int(row.documents),
                            n_observed=int(row.n_observed), available=available,
                            preventive_mh=central if available else None,
                            q1=float(row.q1) if available else None,
                            q3=float(row.q3) if available else None))
    return records


def run():
    revision, protocol_hash = committed_protocol()
    correction = amendment006()
    configuration = json.loads((ROOT / 'data/derived/a16/flow17/configuration.json').read_text())
    check_historical(configuration['historical'])
    state = json.loads((ROOT / 'data/derived/a16/flow17/state.json').read_text())
    if (state['status'] != 'complete' or not state.get('null_controls_passed') or
            state['completed_replicas'] != 1800):
        raise RuntimeError('A16 corrected gate is not complete and passed')
    domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv')
    summary = pd.read_csv(ROOT / 'data/derived/single_removal_mh_summary.csv')
    parameters = pd.read_csv(ROOT / 'config/cost_parameters.csv')
    records = preventive_mh(domain, summary, parameters)
    missing = [r['pn'] for r in records if not r['available']]
    mip_available = importlib.util.find_spec('mip') is not None
    status = 'blocked_missing_mh' if missing else (
        'blocked_missing_solver' if not mip_available else 'inputs_ready')
    sources = ['analysis/a9_preflight.py', 'analysis/preregistro_A16_A9.md',
               'analysis/emenda_A16_A9_006.md', 'config/a4_scale_map.csv',
               'config/cost_parameters.csv', 'data/derived/single_removal_mh_summary.csv',
               'data/derived/stoppages.csv', 'data/derived/a16/flow17/configuration.json',
               'data/derived/a16/flow17/state.json', 'data/derived/a16/flow17/summary.csv']
    result = dict(status=status, protocol_revision=revision, protocol_sha256=protocol_hash,
                  amendment006=correction, a16_controls_passed=True,
                  a9_simulated_replicas=0, pilot_started=False,
                  missing_preventive_mh=missing, mip_importable=mip_available,
                  historical_hashes_checked=len(configuration['historical']),
                  historical_artifacts_unchanged=True,
                  coefficients=records, sources={p: sha(ROOT / p) for p in sources})
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / 'state.json', result)
    pd.DataFrame(records).to_csv(OUT / 'preventive_mh.csv', index=False)
    lines = ['# A9/A10 — conferência anterior ao piloto', '',
             '14/11/2026. O autor autorizou o início após a conclusão de T16.', '',
             'Estado: **' + status + '**. Nenhuma réplica de piloto ou de política gerada.', '',
             'A16 corrigida concluiu 1 800 réplicas e aprovou os controles. Os hashes',
             'históricos foram conferidos e permanecem intactos. O pré-registro e a',
             'emenda 006 correspondem às versões commitadas.', '',
             '## MH preventiva exigida pelo protocolo', '',
             'Fonte: T4, soma de linhas por documento com uma única remoção, mediana por P/N.',
             'As faixas empíricas Q1/Q3 são preservadas. Nenhum coeficiente foi imputado.', '',
             '| P/N | Documentos | Com MH | MH central |',
             '|---|---|---|---|']
    for r in records:
        value = str(r['preventive_mh']) if r['available'] else 'indisponível'
        lines.append(f"| {r['pn']} | {r['documents']} | {r['n_observed']} | {value} |")
    lines += ['', 'O pré-registro A16/A9, seção 6, determina: “Falta de MH não vira zero:',
              'parar a instanciação desse P/N e informar o autor.” Os três P/N sem',
              'coeficiente não têm documentos de remoção única nesta base. Há estimativas',
              'por rateio em documentos compartilhados, mas pertencem à sensibilidade',
              'e não substituem a fonte principal sem emenda explícita do autor.', '',
              'A capacidade de cada visita depende da soma das MH das unidades ativas;',
              'assim, a lacuna impede instanciar a comparação completa pré-especificada.',
              'Não foram excluídos P/N, reduzida a grade ou medidas durações de um piloto',
              'parcial. R de A9 ainda não foi calculado e o orçamento continua em 120 h.', '',
              '## Dependência computacional', '',
              f'python-mip importável no interpretador py -3: **{mip_available}**.',
              'A instalação do solver e seus testes de ótimo/renovação precederão o piloto.',
              'A conferência de insumos não certifica prontidão do simulador/MILP.', '',
              '## Desbloqueio', '',
              'O autor precisa definir a fonte de MH para os três P/N ou autorizar, por',
              'emenda, uma aproximação explícita com suas limitações e sensibilidades.',
              'Manter os 11 P/N e a grade; não escolher valores pelo ganho de política.', '']
    (ROOT / 'analysis/a9_preflight_report.md').write_text('\n'.join(lines), encoding='utf-8')
    check_historical(configuration['historical'])
    print(status + ': ' + ', '.join(missing))
    return result


if __name__ == '__main__':
    run()
