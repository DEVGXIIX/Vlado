"""Synthetic agent deliveries; exercises real stage/publication code, no model."""
import json
import time


def esperar(predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('Estado esperado não foi atingido pela fixture.')


def entrega(stage, tool, refs, answer='Resposta técnica sintética.', *, valor='123'):
    if stage == 'inventario':
        tool({'acao': 'cobertura'})
        return 'Inventário sintético: uma fonte textual; sem validação humana.'
    if stage == 'plano':
        return 'Plano sintético: localizar a declaração e conferir seu contexto.'
    if stage == 'busca':
        hit = tool({'acao': 'buscar', 'consulta': 'Alfabeto'})['resultados'][0]
        tool({'acao': 'ler', 'referencia': hit['referencia']})
        refs['hit'] = hit
        return 'Busca sintética executada: Alfabeto; contexto lido e fonte atribuída.'
    hit = refs['hit']
    if stage == 'geracao_inicial':
        return json.dumps({'texto': 'Geração inicial sintética preservada.', 'achados': [{
            'subquestao': 'O que declara a fonte sintética?', 'redacao': f'A fonte sintética declara valor {valor}.',
            'natureza': 'alegacao_atribuida', 'limitacoes': 'Declaração sintética, sem verificação externa.',
            'evidencias': [{'referencia': hit['referencia'], 'trecho': hit['trecho'].splitlines()[0],
                'papel': 'suporte', 'justificativa': 'A declaração é literal.', 'atribuicao': 'Fonte sintética',
                'contexto': 'Fixture técnica de integração.', 'limitacoes': 'Não é documento real.'}]}]}, ensure_ascii=False)
    if stage == 'revisao':
        tool({'acao': 'ler', 'referencia': hit['referencia']})
        return json.dumps({'texto': 'Revisão sintética pela mesma IA; sem aprovação humana.', 'revisoes': [{
            'achado_id': 'A001', 'suporte': 'sustentado', 'motivo': 'Redação atribuída compatível com a fonte reaberta.',
            'limitacoes': 'Teste técnico sintético.', 'acao': 'manter'}]}, ensure_ascii=False)
    return json.dumps({'texto': answer + f'\n[A001@v1] A fonte sintética declara valor {valor}. [fonte:' + hit['referencia'] + ']',
        'destinos': [{'achado_id': 'A001', 'destino': 'incluido', 'motivo': 'Alegação atribuída revisada.'}]}, ensure_ascii=False)


def completar(manager, identifier, answer='Resposta técnica sintética.'):
    refs = {}
    for stage in ('inventario', 'plano', 'busca', 'geracao_inicial', 'revisao', 'sintese'):
        esperar(lambda: manager.contexts[identifier]['meta'].get('etapa') == stage and
                manager.contexts[identifier]['meta'].get('turn_id'))
        tool = lambda args: manager.ferramenta(identifier, args)[0]
        raw = entrega(stage, tool, refs, answer)
        tool({'acao': 'guardar', 'etapa': stage, 'texto': raw})
        turn = manager.contexts[identifier]['meta']['turn_id']
        manager.rpc.emit('item/completed', {'item': {'id': 'msg-' + turn, 'type': 'agentMessage',
                         'phase': 'final_answer', 'text': 'Etapa sintética entregue.'}})
        manager.rpc.emit('turn/completed', {'turn': {'id': turn, 'status': 'completed'}})
    esperar(lambda: manager.eventos(identifier)['conversa']['estado'] not in
            ('preparando', 'executando', 'publicando', 'aguardando_aprovacao', 'cancelando'))
