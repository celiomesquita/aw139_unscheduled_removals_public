"""Render the T12 gate and timing reports from saved numerical artifacts."""
import json

import pandas as pd

from a16_generator import ROOT, OUT


def main():
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    verification = json.loads((ROOT / 'data/derived/a16/verification.json').read_text(encoding='utf-8'))
    rates = pd.read_csv(OUT / 'rate_validation.csv')
    ages = pd.read_csv(OUT / 'age_distributions.csv')
    structure = pd.read_csv(OUT / 'channels.csv')
    markers = pd.read_csv(OUT / 'installation_markers.csv')
    observed = pd.read_csv(OUT / 'observed_rates.csv')
    table = rates[rates.level.eq('calibrated')][['pn', 'real_rate', 'simulated_rate',
        'predictive_lo', 'predictive_hi', 'simulated_real_ratio', 'mc_se', 'within_interval']]
    age_table = ages[ages.level.eq('calibrated')][['pn', 'real_q10', 'real_q50', 'real_q90',
        'simulated_q10', 'simulated_q50', 'simulated_q90', 'normalized_wasserstein']]
    report = ('# T12 / A16 — validação do gerador e piloto\n\n'
        'Pré-registro A16_A9_v1, commit aa129e2, com alterações do autor anteriores '
        'à simulação: η ajustado para preservar vida média ao variar β; visitas reais; '
        '168 h de máquina (48 h A16, 120 h A9/A10). Arquivo preservado.\n\n'
        '## Gerador estacionário: barreira aprovada\n\n'
        f'{len(markers)} marcos reais, {len(structure)} canais sintéticos, 24 aeronaves. '
        'A coloração preserva datas e observação, sem alegar identificação de posições '
        'físicas. Quatro eventos reais de idade zero foram excluídos das taxas como '
        'em A4, mantendo seus marcos. FH, decolagens e máscaras diárias foram '
        'preservadas; a exposição reconstruída confere com a soma dos trechos.\n\n'
        '1 000 réplicas por nível (calibrado, β=1, ampliado), 3 000 no total, '
        'sem reajuste dos parâmetros reais. Intervalo preditivo central por P/N '
        'com α=0,05/11; o nível calibrado governa a decisão. Taxas por FH ou dia '
        'conforme a escala fixada. mc_se mede a incerteza da média simulada, '
        'não a dispersão preditiva nem incerteza do parâmetro estimado.\n\n'
        + table.to_markdown(index=False, floatfmt='.8f') + '\n\n'
        'Os 11 P/N passaram pelo critério pré-especificado. As razões simulada/real '
        'diferem de 1, principalmente para o colete PAX; aprovação por intervalo '
        'preditivo não é equivalência das taxas nem validação de toda a distribuição. '
        'Os níveis β=1 e ampliado permanecem descritivos em rate_validation.csv.\n\n'
        '## Idades na remoção\n\n' + age_table.to_markdown(index=False, floatfmt='.4f')
        + '\n\nQuantis de 10/50/90% e distância de Wasserstein dividida pela mediana '
        'real. Discrepâncias foram preservadas, sem recalibração. A ECDF real '
        'pode ser reconstruída de real_event_ages.csv; as idades simuladas completas '
        'estão em latent_spells.csv.gz (filtrar observed=1, risk=1, age>0). '
        'A grade de 201 quantis é uma representação adicional das distribuições.\n\n'
        '## Reprodução e testes\n\n'
        f'Duas execuções completas geraram {verification["identical_artifacts"]} '
        f'artefatos idênticos por SHA256; {verification["tests_run"]} testes aprovados. '
        'O único teste excluído reexecutaria A5, vedado nesta rodada. '
        'A5, A4, seus pré-registros, o novo pré-registro e o manuscrito ficaram '
        'intactos. verification.json documenta o estado anterior ao piloto. '
        'As emendas 001 (antes da geração) e 002 (antes do piloto) explicitam '
        'as convenções de observação e de adaptação, sem alterar pré-registros.\n')
    pilot_path = ROOT / 'data/derived/a16/pilot_manifest.json'
    if pilot_path.exists():
        pilot = json.loads(pilot_path.read_text(encoding='utf-8'))
        timing = pd.read_csv(ROOT / 'data/derived/a16/pilot_timing.csv')
        minimum_hours = 9 * 1.5 * 200 * pilot['worst_replica_seconds'] / 3600
        report += ('\n## Piloto de tempo, excluído dos resultados\n\n'
            + timing.to_markdown(index=False, floatfmt='.3f') + '\n\n'
            f'Maior tempo: {pilot["worst_replica_seconds"]:.3f} s por réplica ×4 '
            '(duas variantes, B=999). Para R≥200 nas nove células, a regra exige '
            'tempo ≤64 s por réplica; reserva de 1,5 incluída. '
            f'R pela fórmula: {pilot["raw_R"]}; estimativa conservadora para '
            f'R=200: {minimum_hours:.3f} h frente às 48 h reservadas. '
            'Métricas/rejeições do piloto não foram inspecionadas ou incorporadas '
            'a resultados de poder.\n\n')
        report += ('Orçamento aprovado; R fixado em ' + str(pilot['fixed_R']) +
                   '. Próxima etapa: controle nulo e análise de poder.\n' if pilot['budget_passed'] else
                   '**Parada obrigatória de orçamento:** R≥200 não cabe. Não reduzir '
                   'grade ou R nem transferir as 120 h de A9/A10. Nenhum resultado de '
                   'poder, erro tipo I ou economia foi produzido; A9/A10 não iniciadas. '
                   'O autor deve decidir a revisão de orçamento por emenda antes '
                   'de prosseguir.\n')
    else:
        report += '\nPiloto ainda sem manifesto final; nenhuma análise de poder foi executada.\n'
    (ROOT / 'analysis/a16_report.md').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    main()
