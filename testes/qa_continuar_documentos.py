"""Browser acceptance of versioned continuity; synthetic documents and fake runtime."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from test_codex_integracao import CodexIntegrationTest, FakeServer
from agente_fluxo_fixture import completar, entrega, esperar
from interface_pesquisa import Servidor
from comum import sha256, ler_json
import revisao_humana


class BrowserContinuidade(FakeServer):
    def call(self,method,params=None):
        result=super().call(method,params)
        if method=='turn/start':threading.Thread(target=self.drive,args=(params['input'][0]['text'],result['turn']['id']),daemon=True).start()
        return result

    def drive(self,text,turn):
        time.sleep(.15);number=time.time_ns()
        def tool(args):
            nonlocal number
            number+=1;self.emit('item/tool/call',{'tool':'consultar_acervo','arguments':args,'callId':str(number)},request=number)
            result=self.answer(number)['result']
            if not result['success']:raise ValueError(result)
            return json.loads(result['contentItems'][0]['text'])
        stage=re.search(r'Etapa obrigatória atual: (\w+)\.',text)[1]
        if stage=='inventario':self.refs={}
        if stage=='busca':
            self.refs['hit']=tool({'acao':'buscar','consulta':'Contrato'})['resultados'][0]
            tool({'acao':'ler','referencia':self.refs['hit']['referencia']});raw='Leitura sintética dos novos documentos.'
        elif stage=='comparacao':raw=json.dumps({'comparacoes':[{'anteriores':['A001'],'atuais':['A001'],
            'tipo':'alterada','justificativa':'A nova peça declara 246; antes a fonte declarava 123. Comparação sintética.'}]})
        else:raw=entrega(stage,tool,self.refs,'Resposta sintética com documentos novos.',valor='246')
        tool({'acao':'guardar','etapa':'sintese' if stage=='comparacao' else stage,'texto':raw})
        self.emit('item/completed',{'item':{'id':'msg-'+turn,'type':'agentMessage','text':'Etapa sintética concluída.'}})
        self.emit('turn/completed',{'turn':{'id':turn,'status':'completed'}})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node',required=True);parser.add_argument('--saida',required=True);parser.add_argument('--chrome',default='')
    args=parser.parse_args();fx=CodexIntegrationTest();fx.setUp();server=None
    try:
        chat=fx.manager.perguntar({'caso':'alpha','pergunta':'Pergunta técnica sintética.'})['conversa']
        esperar(lambda:fx.manager.contexts[chat]['meta'].get('turn_id'),timeout=30)
        completar(fx.manager,chat)
        run=fx.manager.contexts[chat]['run']
        detail=revisao_humana.detalhe(fx.root,'alpha','R001','r3_sintese','g1','A001')
        revisao_humana.salvar(fx.root,'alpha','R001','r3_sintese',achado_id='A001',achado_versao=1,
            registros_sha256=detail['registros_sha256'],estado='conferida_no_original')
        before={p:sha256(p) for p in run.rglob('*') if p.is_file()};config=(fx.root/'configuracao.json').read_bytes()
        fx.manager.rpc.close();fx.manager.rpc=None;fx.manager.factory=BrowserContinuidade
        server=Servidor(('127.0.0.1',0),fx.root);server.conversas=fx.manager
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        result=subprocess.run(['node',str(Path(__file__).with_suffix('.cjs')),server.origin,str(Path(args.saida).resolve()),args.chrome,chat],env={**os.environ,'NODE_PATH':args.modulos_node})
        if result.returncode:return result.returncode
        assert all(sha256(p)==digest for p,digest in before.items())
        assert config==(fx.root/'configuracao.json').read_bytes()
        meta=fx.manager.contexts[chat]['meta'];assert meta['rodadas']==['R001','R002'] and meta['corpus_id']=='alpha_v3'
        report=ler_json(fx.root/'execucoes/alpha/R002/saidas/codex_execucao.json')
        assert len(report['etapas_validadas'])==7 and report['estado']=='concluido'
        assert len([1 for method,_ in fx.manager.rpc.calls if method=='turn/start'])==7
        return 0
    finally:
        if server:server.shutdown();server.server_close();thread.join(3)
        fx.doCleanups()


if __name__=='__main__':raise SystemExit(main())
