"""Browser acceptance of selected feedback, with synthetic corpus and fake runtime."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from fixture_achados import Ambiente
from interface_pesquisa import Servidor
from test_codex_integracao import FakeServer
from agente_fluxo_fixture import entrega
from comum import sha256
import revisao_humana


class BrowserObservacoes(FakeServer):
    def call(self, method, params=None):
        result = super().call(method, params)
        if method == 'turn/start':
            threading.Thread(target=self.drive,args=(params['input'][0]['text'],result['turn']['id']),daemon=True).start()
        return result

    def drive(self,text,turn_id):
        time.sleep(.15)
        number=time.time_ns()
        def tool(args):
            nonlocal number
            number+=1
            self.emit('item/tool/call',{'tool':'consultar_acervo','arguments':args,'callId':str(number)},request=number)
            result=self.answer(number)['result']
            if not result['success']:
                raise ValueError(result)
            return json.loads(result['contentItems'][0]['text'])
        stage=re.search(r'Etapa obrigatória atual: (\w+)\.',text)[1]
        if stage=='inventario': self.refs={}
        if stage=='busca':
            hit=tool({'acao':'buscar','consulta':'valor'})['resultados'][0]
            tool({'acao':'ler','referencia':hit['referencia']})
            self.refs['hit']=hit
            raw='Busca sintética com fonte reaberta.'
        else:
            raw=entrega(stage,tool,self.refs,'Resposta sintética após reexame.').replace('123','12')
        tool({'acao':'guardar','etapa':stage,'texto':raw})
        self.emit('item/completed',{'item':{'id':'msg-'+turn_id,'type':'agentMessage','text':'Etapa sintética concluída.'}})
        self.emit('turn/completed',{'turn':{'id':turn_id,'status':'completed'}})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node',required=True)
    parser.add_argument('--saida',required=True)
    parser.add_argument('--chrome',default='')
    args=parser.parse_args()
    fx=Ambiente(); server=None
    try:
        fx.completo(quantidade=12); fx.caso('beta')
        for identifier,note in [('A001','O valor é do contrato inteiro, não de uma parcela. <script>window.RETORNO_INJETADO=true</script>'),
                                ('A002','NÃO SELECIONADA'),('A012','Reexaminar a unidade informada.')]:
            detail=revisao_humana.detalhe(fx.root,'alpha','R001','r2','g2',identifier)
            revisao_humana.salvar(fx.root,'alpha','R001','r2',achado_id=identifier,
                achado_versao=detail['achado']['versao'],registros_sha256=detail['registros_sha256'],
                estado='precisa_de_ajuste',observacao=note)
        before={p:sha256(p) for p in fx.run().rglob('*') if p.is_file()}
        config=(fx.root/'configuracao.json').read_bytes()
        server=Servidor(('127.0.0.1',0),fx.root); server.conversas.factory=BrowserObservacoes
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        result=subprocess.run(['node',str(Path(__file__).with_suffix('.cjs')),server.origin,
                               str(Path(args.saida).resolve()),args.chrome],env={**os.environ,'NODE_PATH':args.modulos_node})
        if result.returncode:
            return result.returncode
        assert all(sha256(p)==digest for p,digest in before.items()),'Arquivos anteriores da rodada foram modificados.'
        assert config==(fx.root/'configuracao.json').read_bytes(),'Seleção global foi alterada.'
        prompts=[p['input'][0]['text'] for m,p in server.conversas.rpc.calls if m=='turn/start']
        assert len(prompts)==6 and all('Contrato inteiro, com contexto revisto.' in p and 'Reexaminar a unidade informada.' in p for p in prompts)
        assert all('NÃO SELECIONADA' not in p for p in prompts)
        receipt=json.loads((fx.root/'execucoes/alpha/R002/saidas/observacoes_humanas_recebidas.json').read_text(encoding='utf-8'))
        assert [item['achado_id'] for item in receipt['observacoes']]==['A012','A001']
        return 0
    finally:
        if server:
            server.shutdown(); server.server_close(); thread.join(timeout=3)
        fx.cleanup()


if __name__=='__main__':
    raise SystemExit(main())
