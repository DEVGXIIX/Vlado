"""Notebook browser acceptance with human test actions and a simulated runtime."""
import argparse
import os
from pathlib import Path
import subprocess
import threading

from test_codex_integracao import CodexIntegrationTest
from qa_codex import BrowserFake
from comum import sha256, ler_json
from cadastrar_documentos import cadastrar
from interface_pesquisa import Servidor
import caderno


class BrowserCaderno(BrowserFake):
    authenticated=True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node',required=True);parser.add_argument('--saida',required=True);parser.add_argument('--chrome',default='')
    args=parser.parse_args();fx=CodexIntegrationTest();fx.setUp();server=None
    try:
        from pypdf import PdfWriter
        pdf=fx.root/'scan.pdf';writer=PdfWriter();writer.add_blank_page(width=300,height=300);writer.write(pdf)
        cadastrar(fx.root,'alpha',[pdf],natureza='sinteticos')
        before={p:sha256(p) for p in fx.root.rglob('*') if p.is_file()}
        server=Servidor(('127.0.0.1',0),fx.root);server.conversas=fx.manager;fx.manager.factory=BrowserCaderno
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        result=subprocess.run(['node',str(Path(__file__).with_suffix('.cjs')),server.origin,str(Path(args.saida).resolve()),args.chrome],env={**os.environ,'NODE_PATH':args.modulos_node})
        if result.returncode:return result.returncode
        assert all(sha256(p)==digest for p,digest in before.items()),'Arquivo anterior ao caderno foi alterado.'
        notes=caderno.listar(fx.root,'alpha',limite=100)
        assert notes['total']==4
        assert {item['registro']['autor'] for item in notes['resultados']}=={'Autora A','Autor B','Editora C','Repórter D'}
        report=ler_json(fx.root/'execucoes/alpha/R001/saidas/codex_execucao.json')
        receipt=ler_json(fx.root/'execucoes/alpha/R001/saidas/caderno_recebido.json')
        assert report['estado']=='concluido' and report['caderno_recebido']['quantidade']==1
        assert receipt['registros'][0]['registro']['tipo']=='cruzamento'
        assert receipt['registros'][0]['registro']['autor']=='Editora C'
        prompts=[p['input'][0]['text'] for m,p in fx.manager.rpc.calls if m=='turn/start']
        assert len(prompts)==6 and all('HIPOTESE_JORNALISTA_CADERNO' in p and 'Editora C' in p for p in prompts)
        assert len(fx.manager.contexts[next(iter(fx.manager.contexts))]['manifest']['documentos'])==2
        return 0
    finally:
        if server:server.shutdown();server.server_close();thread.join(3)
        fx.doCleanups()


if __name__=='__main__':raise SystemExit(main())
