"""Visual acceptance with synthetic PDF, recorded UI events and simulated login."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from test_interface_pesquisa import InterfaceTest
from test_codex_integracao import FakeServer
from test_extracao_cadastro_pdf import pdf_sintetico
from criar_caso import criar_caso
from nova_rodada import criar_rodada
from indice_sqlite import pesquisar
from comum import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node', required=True)
    parser.add_argument('--saida', required=True)
    parser.add_argument('--chrome', default='')
    args = parser.parse_args()
    fixture = InterfaceTest()
    fixture.setUp()
    try:
        pdf = pdf_sintetico(fixture.root / 'Fato_relevante_11_01_2023.pdf', ('Valor sintetico 123.', None))
        criar_caso(fixture.root, 'fontes', 'Americanas — fatos relevantes', [pdf], 'sinteticos')
        run = criar_rodada(fixture.root, 'R001', 'O que este documento informa?', caso='fontes')
        hit = pesquisar(fixture.root, 'fontes', 'R001', 'Valor')['resultados'][0]
        hit.update(rodada='R001', geracao='v1')
        meta = fixture.conversa_sintetica(caso='fontes')
        text = ('## O que o documento informa\n\n'
                '**Valor documentado:** o arquivo sintético informa 123. [fonte:' + hit['referencia'] + ']\n\n'
                '- O valor aparece na **primeira página**.\n- A segunda página está sem texto extraível.\n\n'
                '| Informação | Valor |\n| --- | --- |\n| Registro sintético | **123** |\n\n'
                '> O alcance desta resposta é o documento fornecido.\n\n'
                '**Fonte pendente:** esta citação foi simulada para testar a interface. [fonte:' + 'f' * 64 + ']\n\n'
                '<script>window.INJETADO_POLIMENTO=true</script>\n\n'
                '[Não executar](javascript:alert(1))\n\n'
                '![Não carregar](https://example.test/diagnostico.png)\n\n'
                '```text\n**texto literal em código**\n```')
        raw = run / 'saidas/resposta_sintetica_interface.md'
        raw.write_text(text, encoding='utf-8')
        events = [
            ('pergunta', {'texto': 'O que este documento informa?'}),
            ('escopo', {'caso': 'fontes', 'rodada': 'R001', 'corpus_id': 'fontes_v1', 'modelo': 'fixture sem inferência'}),
            ('etapa', {'etapa': 'busca', 'numero': 3, 'total': 6, 'tentativa': 1}),
            ('resposta', {'item': 'provisoria', 'texto': '**Conferindo** o documento.', 'fase': 'provisoria', 'rodada': 'R001'}),
            ('fonte', hit),
            ('resposta', {'item': 'final', 'texto': text, 'fase': 'final_answer', 'rodada': 'R001', 'publicada': True,
                          'arquivo': str(raw.relative_to(fixture.root)), 'sha256': sha256(raw)}),
        ]
        path = fixture.root / f'conversas/{meta["id"]}/eventos.jsonl'
        path.write_text(''.join(json.dumps({'seq': i, 'tipo': kind, 'dados': data, 'em_utc': '2026-01-01T00:00:00Z'}, ensure_ascii=False) + '\n'
                                for i, (kind, data) in enumerate(events, 1)), encoding='utf-8')
        fixture.server.conversas.factory = FakeServer
        env = {**os.environ, 'NODE_PATH': args.modulos_node}
        return subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), fixture.server.origin,
                               str(Path(args.saida).resolve()), args.chrome], env=env).returncode
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    raise SystemExit(main())
