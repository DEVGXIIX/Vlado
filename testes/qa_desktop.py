"""Regressão desktop e preservação mobile, com documentos e conexão sintéticos."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import uuid

from fixture_achados import Ambiente
from test_codex_integracao import FakeServer
from interface_pesquisa import Servidor
from criar_caso import criar_caso
from nova_rodada import criar_rodada
from indice_sqlite import pesquisar
from comum import escrever_json
import caderno


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', required=True)
    args = parser.parse_args()
    output = Path(args.saida).resolve()
    output.mkdir(parents=True, exist_ok=True)
    fx = Ambiente()
    server = None
    try:
        fx.completo(quantidade=32)
        docs = caderno.documentos(fx.root, 'alpha')
        doc = next(item for item in docs['documentos'] if item['formato'] == '.txt')
        for i in range(22):
            caderno.salvar(fx.root, {'caso':'alpha', 'origem_id':docs['origem_id'],
                'documento_id':doc['documento_id'], 'documento_sha256':doc['sha256'],
                'pagina_pdf':None, 'localizador':'Linha 1', 'trecho':'A fonte declara valor 12.',
                'titulo':f'Trecho sintético {i}', 'anotacao':'', 'autor':'Fixture técnica',
                'tipo':'trecho', 'transcricao_manual':False, 'requisicao_id':uuid.uuid4().hex})
        source = fx.root / 'longo.txt'
        source.write_text('\n'.join(f'Consulta sintética {i}. ' + 'Texto para paginação documental. ' * 12 for i in range(600)), encoding='utf-8')
        criar_caso(fx.root, 'beta', 'Paginação sintética', [source], 'sinteticos')
        criar_rodada(fx.root, 'R001', 'Teste técnico de paginação.', caso='beta')
        hit = pesquisar(fx.root, 'alpha', 'R001', 'valor')['resultados'][0]
        hit.update(rodada='R001', geracao='v1')
        identifier = 'a' * 32
        escrever_json(fx.root / f'conversas/{identifier}/conversa.json', {
            'id': identifier, 'caso': 'alpha', 'titulo': 'Conversa sintética de leitura',
            'estado': 'concluido', 'rodadas': ['R001'], 'criada_em_utc': '2026-01-01T00:00:00Z'})
        events = [('pergunta', {'texto': 'Pergunta técnica sintética.'}),
                  ('escopo', {'caso': 'alpha', 'rodada': 'R001', 'corpus_id': 'alpha_v1', 'modelo': 'fixture sem inferência'}),
                  ('fonte', hit),
                  ('resposta', {'item': 'provisoria', 'texto': 'Atualização sintética.', 'fase': 'provisoria', 'rodada': 'R001'}),
                  ('resposta', {'item': 'final', 'texto': ('## Leitura sintética\n\n' + 'Parágrafo para testar leitura e fontes.\n\n' * 32 + '[fonte:' + hit['referencia'] + ']'),
                                'fase': 'final_answer', 'publicada': True, 'rodada': 'R001'})]
        (fx.root / f'conversas/{identifier}/eventos.jsonl').write_text(''.join(json.dumps({
            'seq': i, 'tipo': kind, 'dados': data, 'em_utc': '2026-01-01T00:00:00Z'}, ensure_ascii=False) + '\n'
            for i, (kind, data) in enumerate(events, 1)), encoding='utf-8')
        server = Servidor(('127.0.0.1', 0), fx.root)
        server.conversas.factory = FakeServer
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), server.origin,
                               str(output), identifier], env=os.environ.copy()).returncode
    finally:
        if server:
            server.shutdown()
            server.server_close()
        fx.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
