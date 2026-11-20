"""Metadata-only closure after the single additional process has exited."""
import json
import math
import psutil
from datetime import datetime
from amendment015.state import ROOT,OUT,START,atomic,digest,freeze,ledger,utcnow
from amendment015_extra06 import RUN,integrity,prefix_matches


def run():
    ledger_data=json.loads((OUT/'time_ledger.json').read_text());a=ledger_data['additional06']
    spec=json.loads((RUN/'configuration.json').read_text());launch=json.loads((RUN/'launch.json').read_text())
    try:
        p=psutil.Process(launch['pid'])
        if p.is_running() and p.status()!=psutil.STATUS_ZOMBIE:raise RuntimeError('ADDITIONAL06_PROCESS_STILL_ALIVE')
    except psutil.NoSuchProcess:pass
    config=json.loads((OUT/'configuration.json').read_text());integrity(config,a)
    for name,old in spec['preserved_certificates'].items():
        file=OUT/'references'/f'{name}_certificate.json'
        assert digest(file)==old['sha256'] and file.stat().st_mtime_ns==old['mtime_ns']
    assert prefix_matches((ROOT/'analysis/emenda_A16_A9_015.md').read_bytes(),a['original_amendment_prefix_bytes'],a['original_amendment_prefix_sha256'])
    deadline=datetime.fromisoformat(a['deadline_utc']);begin=datetime.fromisoformat(a['preparation_start_utc'])
    cert_path=OUT/'references/06_certificate.json';success=False
    if cert_path.exists():
        cert=json.loads(cert_path.read_text())
        success=(cert['status']=='complete' and cert['diagnostics']['global_discrete_search'] and
                 datetime.fromisoformat(cert['finished_utc'])<=deadline and
                 cert['input_sha256']==digest(OUT/'references/06_inputs.json'))
    rows=[]
    if success:
        for item in config['sample']:
            path=OUT/'references'/f"{item['id']}_certificate.json";c=json.loads(path.read_text())
            assert c['status']=='complete' and c['input_sha256']==digest(OUT/'references'/f"{item['id']}_inputs.json")
            rows.append(dict(id=item['id'],certificate=path.name,sha256=digest(path),age=c['age'],infinite=c['infinite'],rate=c['rate'],subdivisions=4,input_sha256=c['input_sha256']))
        manifest=dict(status='complete',N=9,seed=20261117015,configuration_sha256=digest(OUT/'configuration.json'),
            age_source_sha256=digest(ROOT/'analysis/amendment015/age.py'),references=rows,
            additional06_configuration_sha256=digest(RUN/'configuration.json'))
        freeze(OUT/'references/manifest.json',manifest)
        from amendment015.age import require_manifest
        require_manifest(OUT/'references/manifest.json')
        end=datetime.fromisoformat(cert['finished_utc'])
        status='certified_stop_for_audit'
        scope='Await author audit before g verification; no RQ4 effect inference'
    else:
        assert not (OUT/'references/manifest.json').exists()
        end=min(utcnow(),deadline);status='not_certified_no_further_extension'
        scope='RQ4 protocol plus feasibility pilot; full evaluation future work; calibration not validated'
    progress=json.loads((RUN/'progress.json').read_text())
    current=ledger('additional06_final_STOP')
    current['additional06'].update(status=status,closed_utc=utcnow().isoformat(),
        execution_end_utc=end.isoformat(),elapsed_seconds=(end-begin).total_seconds(),
        remaining_seconds=0. if not success else max(0.,(deadline-end).total_seconds()),
        calibration_validated=False,RQ4_scope=scope,additional_execution_permitted=False,
        certificate_06_created=success,process_confirmed_dead=True,progress=progress)
    current['references_certified']=9 if success else 8;current['references_pending']=[] if success else ['06']
    atomic(OUT/'time_ledger.json',current)
    summary=dict(status=status,success=success,preparation_start_utc=begin.isoformat(),deadline_utc=deadline.isoformat(),
        calculation_started_utc=launch['calculation_started_utc'],execution_end_utc=end.isoformat(),
        elapsed_seconds=(end-begin).total_seconds(),pid=launch['pid'],process_confirmed_dead=True,
        preserved_eight_certificates_unchanged=True,committed_amendment_prefix_unchanged=True,
        progress=progress,full_manifest_frozen=success,calibration_validated=False,
        verification_started=False,T20_started=False,main_started=False,RQ4_scope=scope,
        global_consumed_seconds=current['consumed_seconds'],global_remaining_seconds=current['remaining_seconds'],
        audited_utc=current['updated_utc'])
    atomic(RUN/'final_summary.json',summary);atomic(RUN/'state.json',summary);atomic(OUT/'state.json',summary)
    if success:
        old=OUT/'references/06_checkpoint.json'
        freeze(RUN/'prior_reference06_checkpoint.json',json.loads(old.read_text()))
        atomic(old,dict(status='complete',id='06',pid=launch['pid'],certificate='06_certificate.json',
            certificate_sha256=digest(cert_path),input_sha256=digest(OUT/'references/06_inputs.json'),
            additional_execution_configuration_sha256=digest(RUN/'configuration.json')))
    text=(f"# Emenda 015 — execução adicional única de 06\n\n"
          f"Estado: **{status}**. PID {launch['pid']} confirmado encerrado.\n\n"
          f"Preparação: {begin.isoformat()}; limite rígido: {deadline.isoformat()}. "
          f"Consumo desta execução, incluindo preparação: {(end-begin).total_seconds()/3600:.6f} h. "
          f"O orçamento global foi atualizado às {current['updated_utc']}: "
          f"C = {current['consumed_seconds']/3600:.6f} h; saldo = {current['remaining_seconds']/3600:.6f} h. "
          f"Esse segmento já pertence a C e não é somado novamente.\n\n"
          f"O adendo datado foi acrescentado antes da execução. Os bytes do texto commitado em 2d7e19d "
          f"permanecem como prefixo idêntico. Oito certificados foram preservados em conteúdo e mtime. "
          f"Código numérico, configuração, float64, grade de ¼ de dia, parâmetros, pesos, semente, "
          f"amostra, controles e desempates permaneceram iguais. A versão memmap e a telemetria "
          f"somente leitura mantiveram seus hashes. A única substituição em memória foi a checagem "
          f"do relógio expirado pelo novo prazo expressamente autorizado; as funções numéricas não foram alteradas.\n\n"
          f"Execução isolada em um único processo Python, sem processos filhos, recomeçando do zero. "
          f"Não houve outra referência ou processo do executor em paralelo. O limite foi armado "
          f"com SIGALRM de ação padrão do sistema operacional, inclusive durante chamadas nativas. "
          f"O início das 8 h foi registrado na preparação, sem reinício nem extensão.\n\n"
          f"Última telemetria: {progress['utc']}. Fases: {progress['phases_constructed']}/{progress['phases_total']} "
          f"({100*progress['phases_fraction']:.6f}%). Quebras por fase: "
          f"{progress['phase_visit_breakpoints_advanced']}/{progress['phase_visit_breakpoints_total']} "
          f"({100*(progress['breakpoints_fraction'] or 0):.6f}%). As quebras são entradas finitas por fase "
          f"com multiplicidade, não a fração de idades distintas do objetivo.\n\n")
    if success:
        text+="As nove referências estão certificadas. O manifesto completo foi congelado e conferido, com hashes, em `data/derived/a9/amendment015/references/manifest.json`. A calibração ainda não está validada: parada para auditoria antes de g≤0,005.\n\n"
    else:
        text+="06 não foi certificado nesta única execução adicional. Não há manifesto completo e não há nova extensão. A calibração fica não validada. Por decisão expressa do autor, a RQ4 passa a protocolo mais piloto de viabilidade e a avaliação completa fica como trabalho futuro. Esse enquadramento não declara concluídos T20 nem o ensaio técnico de cinco réplicas.\n\n"
    text+="Nenhum limiar barato, verificação g, T20, ensaio técnico ou execução principal foi iniciado. Nenhum ganho ou alarme A9/A10 foi aberto. Nenhuma grade, política, R, amostra ou precisão foi reduzida. Nenhum commit foi realizado.\n\nEvidências: `additional06/configuration.json`, `launch.json`, `progress.json`, `progress.jsonl`, `resources.json`, `final_summary.json` e `time_ledger.json`.\n"
    (ROOT/'analysis/a9_amendment015_extra06_report.md').write_text(text)
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':run()
