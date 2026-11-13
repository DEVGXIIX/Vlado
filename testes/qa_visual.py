"""Aceitação da interface aplicada, exclusivamente com armazenamento e respostas sintéticos."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading

from fixture_achados import Ambiente
from test_codex_integracao import FakeServer
from interface_pesquisa import Servidor
from comum import escrever_json
from indice_sqlite import pesquisar


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
        hit = pesquisar(fx.root, 'alpha', 'R001', 'valor')['resultados'][0]
        hit.update(rodada='R001', geracao='v1')
        chat = 'a' * 32
        escrever_json(fx.root / f'conversas/{chat}/conversa.json', {
            'id': chat, 'caso': 'alpha', 'titulo': 'Conversa sintética de conferência',
            'estado': 'concluido', 'rodadas': ['R001'], 'criada_em_utc': '2026-01-01T00:00:00Z'})
        events = [('pergunta', {'texto': 'Pergunta técnica sintética de apresentação.'}),
                  ('escopo', {'caso': 'alpha', 'rodada': 'R001', 'corpus_id': 'alpha_v1', 'modelo': 'fixture sem inferência'}),
                  ('fonte', hit),
                  ('resposta', {'item': 'final', 'texto': '## Leitura sintética com fonte\n\nA fonte declara valor 12. O registro não comprova pagamento. [fonte:' + hit['referencia'] + ']\n\n### O que ainda falta verificar\n\nEste conteúdo existe apenas para testar a interface, sem execução de modelo.',
                                'fase': 'final_answer', 'publicada': True, 'rodada': 'R001'})]
        (fx.root / f'conversas/{chat}/eventos.jsonl').write_text(''.join(json.dumps({
            'seq': i, 'tipo': kind, 'dados': data, 'em_utc': '2026-01-01T00:00:00Z'}, ensure_ascii=False) + '\n'
            for i, (kind, data) in enumerate(events, 1)), encoding='utf-8')
        server = Servidor(('127.0.0.1', 0), fx.root)
        server.conversas.factory = FakeServer
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), server.origin,
                               str(output), chat], env=os.environ.copy()).returncode
    finally:
        if server:
            server.shutdown()
            server.server_close()
        fx.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
