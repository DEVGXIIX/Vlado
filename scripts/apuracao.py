"""Editable human notebook, versioned separately from documents and AI outputs."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid

import caderno
import indice_achados
from comum import dentro, escrever_json, ler_json, pasta_preparacao, sha256
from indice_sqlite import ler_passagem, caminho_rodada
import lixeira

OPERACOES = ('apuracao-listar', 'apuracao-salvar', 'apuracao-excluir',
             'apuracao-adicionar', 'apuracao-exportar', 'apuracao-original')


def _pasta(root, case):
    caderno._pasta(root, case)  # Same case validation and trash policy, no source reads.
    return dentro(root, f'casos/{case}/apuracao')


def listar(root, case):
    folder = _pasta(root, case)
    paths = sorted((folder / 'revisoes').glob('*.json'))
    if not paths:
        return {'esquema': 1, 'caso': case, 'revisao': 0, 'notas': [], 'requisicoes': {}}
    state = ler_json(paths[-1])
    if state.get('caso') != case or state.get('esquema') != 1 or not isinstance(state.get('notas'), list):
        raise ValueError('Caderno editável inválido; os registros foram preservados.')
    return state


def _nota(state, identifier):
    note = next((n for n in state['notas'] if n['id'] == identifier), None)
    if note is None:
        raise ValueError('Nota não encontrada nesta apuração. Atualize o caderno.')
    return note


def _selecao(text, source):
    caderno._texto(text, 'Texto selecionado', 12000)
    if text not in source:
        raise ValueError('A seleção não pertence ao trecho de origem. Selecione novamente.')
    return text


def _evidencia(root, case, data):
    """Resolve all attribution server-side; never trust browser filenames or pages."""
    run = data.get('rodada')
    lixeira.conferir_disponivel(root, case, rodada=run)
    common = {'caso': case, 'rodada': run}
    if data.get('tipo') == 'pesquisa':
        generation = data.get('geracao', 'v1')
        passage = ler_passagem(root, case, run, data.get('referencia'), geracao=generation)['passagem']
        selected = _selecao(data.get('texto'), passage['trecho'])
        source = {**common, 'tipo': 'pesquisa', 'geracao': generation,
                  'referencia': passage['referencia'], 'texto_selecionado': selected,
                  'documentos': [{**passage, 'localizador': f"Linhas {passage['linha_inicio']}–{passage['linha_fim']}"}]}
    elif data.get('tipo') == 'ia':
        revision, generation = data.get('revisao'), data.get('geracao_achados')
        claim = indice_achados.detalhe(root, case, run, revision, generation, data.get('achado_id'))['achado']
        if claim['versao'] != data.get('achado_versao'):
            raise ValueError('A versão do achado mudou. Selecione novamente.')
        evidence_id = data.get('evidencia_id')
        evidences = [e for e in claim['evidencias'] if any(v['evidencia_id'] == e['id'] for v in claim['vinculos'])]
        if evidence_id:
            evidences = [e for e in evidences if e['id'] == evidence_id]
            if not evidences:
                raise ValueError('Evidência fora deste achado.')
        selected = _selecao(data.get('texto'), evidences[0]['trecho'] if evidence_id else claim['redacao'])
        docs = []
        for ev in evidences:
            # Validates originals, textual context and hashes using the existing contract.
            indice_achados.evidencia(root, case, run, revision, ev['id'])
            loc = ev['localizador']
            docs.append({**ev, 'pagina_pdf': loc.get('pagina_pdf'),
                         'localizador': loc.get('descricao') or (f"Linhas {loc['linha_inicio']}–{loc['linha_fim']}" if loc.get('linha_inicio') else loc['tipo'])})
        source = {**common, 'tipo': 'ia', 'revisao': revision, 'geracao_achados': generation,
                  'achado_id': claim['id'], 'achado_versao': claim['versao'],
                  'evidencia_id': evidence_id, 'texto_selecionado': selected, 'documentos': docs}
    else:
        raise ValueError('Origem de evidência inválida.')
    # Add human-readable names from this run's frozen manifest, never another case.
    origin, _ = caderno.contexto(root, case, run)
    names = {d['id']: d.get('nome_recebido', Path(d['arquivo']).name) for d in origin['manifesto']['documentos']}
    for doc in source['documentos']:
        doc['nome_documento'] = names.get(doc['documento_id'], doc['documento_id'])
    return source


def alterar(root, operation, data):
    case = data.get('caso')
    folder = _pasta(root, case)
    request = data.get('requisicao_id')
    if not isinstance(request, str) or not re.fullmatch(r'[a-f0-9]{32}', request):
        raise ValueError('Identidade de salvamento inválida.')
    digest = caderno._hash(data)
    with caderno._trava(folder):
        state = deepcopy(listar(root, case))
        if request in state['requisicoes']:
            if state['requisicoes'][request] != digest:
                raise ValueError('Esta tentativa já foi usada com outro conteúdo.')
            return state
        if type(data.get('revisao')) is not int or data['revisao'] != state['revisao']:
            raise ValueError('O caderno mudou em outra janela. Reabra as notas antes de salvar; copie seu texto para preservá-lo.')
        now = datetime.now(timezone.utc).isoformat()
        identifier = data.get('nota_id')
        if operation == 'apuracao-excluir':
            note = _nota(state, identifier)
            state['notas'].remove(note)
        else:
            if identifier:
                note = _nota(state, identifier)
            else:
                note = {'id': 'E' + uuid.uuid4().hex, 'titulo': 'Nova nota', 'texto': '',
                        'fontes': [], 'criado_em_utc': now}
                state['notas'].append(note)
            if operation == 'apuracao-salvar':
                note['titulo'] = caderno._texto(data.get('titulo'), 'Título', 200)
                text = data.get('texto')
                caderno._texto(text, 'Nota', 200000, vazio=True)
                note['texto'] = text  # Keep Markdown whitespace intact.
            elif operation == 'apuracao-adicionar':
                source = _evidencia(root, case, data.get('origem', {}))
                source['id'] = 'F' + uuid.uuid4().hex
                note['fontes'].append(source)
                if not identifier:
                    note['titulo'] = 'Seleção da IA' if source['tipo'] == 'ia' else 'Seleção documental'
                number = len(note['fontes'])
                quote = '\n'.join('> ' + line for line in source['texto_selecionado'].splitlines())
                note['texto'] += ('\n\n' if note['texto'] else '') + quote + f'\n\n[Fonte {number}]'
                caderno._texto(note['texto'], 'Nota', 200000, vazio=True)
            else:
                raise ValueError('Operação de edição desconhecida.')
            note['atualizado_em_utc'] = now
        state['revisao'] += 1
        state['requisicoes'][request] = digest
        if len(caderno._canon(state)) > 8 * 1024 * 1024:
            raise ValueError('O caderno excede 8 MB. Reduza o conteúdo antes de salvar.')
        target = folder / 'revisoes' / f"{state['revisao']:010d}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        with pasta_preparacao(folder, '.preparacao_') as staging:
            staged = staging / 'caderno.json'
            escrever_json(staged, state, exclusivo=True)
            staged.rename(target)
        return state


def original(root, data):
    state = listar(root, data.get('caso'))
    note = _nota(state, data.get('nota_id'))
    source = next((s for s in note['fontes'] if s['id'] == data.get('fonte_id')), None)
    if not source:
        raise ValueError('Fonte não encontrada nesta nota.')
    index = data.get('documento_indice')
    if type(index) is not int or not 0 <= index < len(source['documentos']):
        raise ValueError('Documento fora da fonte selecionada.')
    lixeira.conferir_disponivel(root, state['caso'], rodada=source['rodada'])
    doc = source['documentos'][index]
    path = dentro(caminho_rodada(root, state['caso'], source['rodada']), doc['original'])
    if sha256(path) != doc['original_sha256']:
        raise ValueError('Hash da fonte divergente; a nota foi preservada.')
    return path
