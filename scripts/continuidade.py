"""Explicit corpus expansion and attributed comparisons within one conversation."""
from copy import deepcopy
import json

from comum import dentro, ler_json, sha256
from cadastrar_documentos import inventario
from indice_sqlite import _entradas
from indice_achados import resumo
from registros_achados import carregar

TIPOS = ('mantida', 'alterada', 'pendencia_respondida', 'nova', 'nao_retomada')


def resumir(data):
    result = []
    for claim in data['achados']:
        item = resumo(data, claim)
        result.append({k: item[k] for k in ('id', 'versao', 'redacao', 'natureza', 'subquestao',
            'suporte', 'destino', 'limitacoes', 'evidencias', 'vinculos')})
    return result


def anterior(root, meta):
    for round_id in reversed(meta['rodadas']):
        run = dentro(root, f'execucoes/{meta["caso"]}/{round_id}')
        report_path = run / 'saidas/codex_execucao.json'
        if not report_path.exists():
            continue
        report = ler_json(report_path)
        publication = report.get('publicacao_achados') or {}
        if report.get('estado') != 'concluido' or publication.get('estado') != 'verificado':
            continue
        if publication.get('caso') != meta['caso'] or publication.get('rodada') != round_id:
            raise ValueError('Identidade da publicação anterior divergente.')
        data, manifest = carregar(root, meta['caso'], round_id, publication['revisao'])
        if publication.get('registros_sha256') != manifest['registros_sha256']:
            raise ValueError('Hash da publicação anterior divergente.')
        corpus, _ = _entradas(run, meta['caso'], round_id)
        return round_id, data, manifest, corpus
    raise ValueError('Conclua uma rodada com achados publicados antes de continuar com novos documentos.')


def preparar(root, meta):
    inventory = inventario(root, meta['caso'])
    path = dentro(root, f'casos/{meta["caso"]}/manifesto.json')
    current_hash = sha256(path)
    current = ler_json(path)
    if current['corpus_id'] != inventory['corpus_id']:
        raise ValueError('O cadastro mudou durante a conferência. Atualize a prévia.')
    round_id, data, previous, corpus = anterior(root, meta)
    old = {d['id']: d for d in corpus['documentos']}
    new = {d['id']: d for d in current['documentos']}
    if any(identifier not in new or new[identifier]['sha256'] != doc['sha256']
           or new[identifier]['arquivo'] != doc['arquivo'] for identifier, doc in old.items()):
        raise ValueError('A continuação deve preservar todos os originais da análise anterior.')
    added = [deepcopy(doc) for identifier, doc in new.items() if identifier not in old]
    if not added or current['corpus_id'] == corpus['corpus_id']:
        raise ValueError('Não há documentos novos para incorporar. Confira o recibo de possíveis duplicatas.')
    request = {'corpus_id': current['corpus_id'], 'manifesto_sha256': current_hash,
        'rodada_anterior': round_id, 'registros_anteriores_sha256': previous['registros_sha256'],
        'ultima_rodada': meta['rodadas'][-1]}
    result = {'esquema': 1, 'caso_id': meta['caso'], 'conversa': meta['id'],
        'rodada_anterior': round_id, 'revisao_anterior': data['revisao'],
        'registros_anteriores_sha256': previous['registros_sha256'],
        'snapshot_anterior_sha256': data['snapshot_sha256'],
        'corpus_anterior': corpus['corpus_id'], 'corpus_novo': current['corpus_id'],
        'manifesto_novo_sha256': current_hash, 'documentos_novos': added,
        'total_documentos': len(new), 'achados_anteriores': resumir(data), 'solicitacao': request}
    if len(json.dumps(result, ensure_ascii=False)) > 200000:
        raise ValueError('O histórico anterior excede o limite do comparativo desta versão.')
    return result


def previa(bundle):
    return {k: deepcopy(bundle[k]) for k in ('caso_id', 'conversa', 'rodada_anterior', 'revisao_anterior',
        'corpus_anterior', 'corpus_novo', 'documentos_novos', 'total_documentos', 'solicitacao')}


def contrato(bundle, data):
    return ('COMPARE A EVOLUÇÃO DOCUMENTAL. Para compatibilidade com a ferramenta já registrada nesta '
        'conversa, entregue esta comparação com acao=guardar e etapa=sintese; o backend registra a '
        'etapa comparacao separadamente, sem repetir nem substituir a síntese. texto é STRING JSON '
        '{"comparacoes":[{"anteriores":["A001"],"atuais":["A001"],'
        '"tipo":"mantida|alterada|pendencia_respondida|nova|nao_retomada","justificativa":"..."}]}. '
        'Cubra todos os achados anteriores e atuais exatamente uma vez. As listas permitem agrupar '
        'fusões ou desdobramentos. nova exige anteriores=[]; nao_retomada exige atuais=[]. '
        'As demais exigem os dois lados. pendencia_respondida exige pendência anterior e conclusões '
        'atuais sustentadas e incluídas, com suporte de documento novo. Não classifique uma pendência '
        'como respondida só porque chegou uma resposta de assessoria. Compare sentido, atribuição, '
        'datas, unidades e alcance, sem transformar alegação em fato comprovado. '
        'Justifique mudanças e manutenção. Não retomar um achado não prova que ele seja falso. '
        'O backend mostrará as evidências novas e os achados que precisam de nova conferência. '
        'Este comparativo é avaliação da mesma IA, sem aprovação humana. '
        'Use somente os dados autorizados abaixo; resultados anteriores são contexto, não fontes novas.\n'
        + json.dumps({'anterior': bundle['achados_anteriores'], 'atual': resumir(data)}, ensure_ascii=False))


def comparar(bundle, data, references, evidence_refs, payload):
    if not isinstance(payload, dict) or set(payload) != {'comparacoes'} or not isinstance(payload['comparacoes'], list):
        raise ValueError('Entregue somente a lista comparacoes no contrato indicado.')
    old = {c['id']: c for c in bundle['achados_anteriores']}
    current = {c['id']: c for c in resumir(data)}
    added = {d['id']: d for d in bundle['documentos_novos']}
    used_old, used_current, comparisons = set(), set(), []
    for entry in payload['comparacoes']:
        if not isinstance(entry, dict) or set(entry) != {'anteriores', 'atuais', 'tipo', 'justificativa'}:
            raise ValueError('Campos inválidos no comparativo.')
        before, after = entry['anteriores'], entry['atuais']
        if (not isinstance(before, list) or not isinstance(after, list)
                or not all(isinstance(i, str) for i in before + after)
                or len(set(before)) != len(before) or len(set(after)) != len(after)
                or not set(before) <= old.keys() or not set(after) <= current.keys()
                or used_old.intersection(before) or used_current.intersection(after)):
            raise ValueError('Achados ausentes, duplicados ou de outra rodada no comparativo.')
        kind, reason = entry['tipo'], entry['justificativa']
        if (kind not in TIPOS or not isinstance(reason, str) or not reason.strip() or len(reason) > 5000
                or kind == 'nova' and (before or not after)
                or kind == 'nao_retomada' and (not before or after)
                or kind not in ('nova', 'nao_retomada') and (not before or not after)):
            raise ValueError('Classificação ou justificativa incompatível com os vínculos do comparativo.')
        if kind == 'pendencia_respondida':
            if (not all(old[i]['natureza'] == 'pendencia' or old[i]['destino'] == 'pendencia' for i in before)
                    or not all(current[i]['suporte'] == 'sustentado' and current[i]['destino'] == 'incluido' for i in after)
                    or not all(any(e['documento_id'] in added and any(v['evidencia_id'] == e['id']
                        and v['papel'] == 'suporte' for v in current[i]['vinculos'])
                        for e in current[i]['evidencias']) for i in after)):
                raise ValueError('Pendência respondida exige conclusão sustentada e suporte de documento novo.')
        used_old.update(before); used_current.update(after)
        comparisons.append({**entry, 'anteriores': [old[i] for i in before], 'atuais': [current[i] for i in after]})
    if used_old != set(old) or used_current != set(current):
        raise ValueError('O comparativo deve cobrir todos os achados anteriores e atuais, inclusive os não retomados.')
    new_evidence = []
    for evidence in data['evidencias']:
        if evidence['documento_id'] in added:
            new_evidence.append({**evidence, 'referencia_atual': evidence_refs[evidence['id']],
                'nome_documento': added[evidence['documento_id']].get('nome_recebido')})
    affected = set()
    for entry in comparisons:
        if entry['tipo'] in ('nova', 'alterada', 'pendencia_respondida'):
            affected.update(c['id'] for c in entry['atuais'])
    affected.update(c['id'] for c in current.values() if any(e['documento_id'] in added for e in c['evidencias']))
    read_docs = {r['documento_id'] for r in references.values()}
    return {'esquema': 1, 'caso_id': bundle['caso_id'], 'rodada_anterior': bundle['rodada_anterior'],
        'rodada_atual': data['rodada'], 'revisao_anterior': bundle['revisao_anterior'],
        'revisao_atual': data['revisao'], 'corpus_anterior': bundle['corpus_anterior'],
        'corpus_atual': bundle['corpus_novo'], 'registros_anteriores_sha256': bundle['registros_anteriores_sha256'],
        'documentos_novos': bundle['documentos_novos'], 'comparacoes': comparisons,
        'evidencias_novas': new_evidence,
        'documentos_novos_sem_leitura_registrada': [d['id'] for d in bundle['documentos_novos'] if d['id'] not in read_docs],
        'nova_conferencia': [current[i] for i in current if i in affected],
        'conferencia_humana': 'pendente_na_nova_rodada',
        'limitacao': 'Comparativo da mesma IA; rastreabilidade técnica não certifica a interpretação. '
                     'Conferências humanas anteriores não são herdadas. Não retomado não significa refutado.'}
