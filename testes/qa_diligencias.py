"""Synthetic follow-up browser acceptance: no messages sent and no real model inference."""
import argparse
import os
from pathlib import Path
import subprocess
import threading

from test_codex_integracao import CodexIntegrationTest
from agente_fluxo_fixture import completar
from qa_continuar_documentos import BrowserContinuidade
from comum import ler_json, sha256
from interface_pesquisa import Servidor
import diligencias


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node',required=True);parser.add_argument('--saida',required=True);parser.add_argument('--chrome',default='')
    args=parser.parse_args();fx=CodexIntegrationTest();fx.setUp();server=None
    try:
        chat=fx.start();completar(fx.manager,chat)
        run=fx.manager.contexts[chat]['run'];before={p:sha256(p) for p in run.rglob('*') if p.is_file()}
        fx.manager.rpc.close();fx.manager.rpc=None;fx.manager.factory=BrowserContinuidade
        server=Servidor(('127.0.0.1',0),fx.root);server.conversas=fx.manager
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        result=subprocess.run(['node',str(Path(__file__).with_suffix('.cjs')),server.origin,str(Path(args.saida).resolve()),args.chrome,chat],env={**os.environ,'NODE_PATH':args.modulos_node})
        if result.returncode:return result.returncode
        assert all(sha256(p)==digest for p,digest in before.items()),'Rodada anterior alterada.'
        items=diligencias.listar(fx.root,'alpha')['resultados'];assert len(items)==2
        item=next(i for i in items if i['diligencia']['origem']['autor']=='IA')
        assert item['diligencia']['estado']=='resposta_recebida' and len(item['historico'])==3
        report=ler_json(fx.root/'execucoes/alpha/R002/saidas/codex_execucao.json')
        assert report['estado']=='concluido' and len(report['etapas_validadas'])==7
        assert report['diligencias_recebidas']['quantidade']==1
        prompts=[p['input'][0]['text'] for m,p in fx.manager.rpc.calls if m=='turn/start']
        assert len(prompts)==7 and all('RESPOSTA_DILIGENCIA_BROWSER' in p for p in prompts)
        assert len(fx.manager.contexts[chat]['manifest']['documentos'])==2
        assert len(fx.manager.contexts[chat]['meta']['rodadas'])==2
        return 0
    finally:
        if server:server.shutdown();server.server_close();thread.join(3)
        fx.doCleanups()


if __name__=='__main__':raise SystemExit(main())
