"""Optional headless browser acceptance. Creates temporary synthetic cases only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fixture_achados import Ambiente
from registros_achados import publicar
from indice_achados import construir
from interface_pesquisa import Servidor
from comum import sha256


class AmbienteInterface(Ambiente):
    """Include source markup as inert text in a properly hashed synthetic briefing."""

    def briefing(self, data, name='saidas/08_briefing.md'):
        super().briefing(data, name)
        source = self.run(data['caso_id']) / name
        source.write_text('# Briefing sintético\n' + source.read_text(encoding='utf-8')
                          + '\n<script>window.INJETADO_BRIEFING = true</script>\n', encoding='utf-8')
        next(a for a in data['artefatos'] if a['arquivo'] == name)['sha256'] = sha256(source)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--node',default='node')
    p.add_argument('--modulos-node')
    p.add_argument('--chrome')
    p.add_argument('--saida',required=True)
    args=p.parse_args()
    output=Path(args.saida).resolve(); output.mkdir(parents=True,exist_ok=True)
    fx=AmbienteInterface()
    server=None
    try:
        _,revised,_,second=fx.completo(quantidade=14)
        third=fx.sucessora(revised,second,'r3')
        third['conferencias_humanas'].append({'achado_id':'A001','versao':2,'retorno_literal_ou_referencia':'Retorno sintético: conferido somente o número 12.',
            'alcance':'Apenas o número declarado, teste técnico.','decisao':'confirmacao','responsavel':None,'fontes_informadas':[]})
        third['destinos'].append({'achado_id':'A002','versao':1,'destino':'retirado','motivo':'Retirada sintética para teste.',
            'briefing':None,'revisao_suporte':None})
        third['procedencia'].append({'etapa':'retorno_humano','artefatos':[],'ferramentas':['fixture sintética'],'modelo_informado_ou_observado':None})
        fx.relatorio(third,'saidas/09_retorno_humano.md','retorno_humano','A001@v2: retorno sintético parcial, apenas número 12.',-1)
        publicar(fx.root,'alpha','R001',third); construir(fx.root,'alpha','R001','r3','g3')
        fx.caso('beta',indice=False)  # old round: no structured records
        fx.caso('gamma',indice=False)
        empty=fx.dados('gamma',indexed=False); fx.vazio_revisado(empty)
        publicar(fx.root,'gamma','R001',empty); construir(fx.root,'gamma','R001','r2','g2')
        fx.caso('delta',indice=False)
        pending=fx.dados('delta',indexed=False)
        pending['achados']=pending['achados'][1:]; pending['vinculos']=[]
        fx.sincronizar_brutos(pending)
        pending_receipt=publicar(fx.root,'delta','R001',pending)  # r1: no derived findings DB
        pending2=fx.sucessora(pending,pending_receipt,'r2')
        pending2['revisoes_assistidas'].append({'achado_id':'A002','versao':1,'suporte':'nao_sustentado',
            'motivo':'Sem fonte suficiente.','fontes_reabertas':[],'limitacoes':'Teste sintético.','acao':'pendencia'})
        pending2['procedencia'].append({'etapa':'revisao','artefatos':[],'ferramentas':['fixture sintética'],'modelo_informado_ou_observado':None})
        fx.relatorio(pending2,'saidas/06_insuficiencia.md','insuficiencia','A002: permanece pendência sem suporte.',-1)
        publicar(fx.root,'delta','R001',pending2); construir(fx.root,'delta','R001','r2','g2')
        fx.caso('epsilon',indice=False)
        corrupt=fx.dados('epsilon',indexed=False)
        publicar(fx.root,'epsilon','R001',corrupt); construir(fx.root,'epsilon','R001','r1','g1')
        (fx.run('epsilon')/'saidas/achados/indices/g1/achados.sqlite').write_bytes(b'invalid synthetic database')
        server=Servidor(('127.0.0.1',0),fx.root)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        env=os.environ.copy()
        if args.modulos_node:
            env['NODE_PATH']=str(Path(args.modulos_node).resolve())
        result=subprocess.run([args.node,str(Path(__file__).with_suffix('.cjs')),server.origin,str(output),args.chrome or ''],env=env,check=False)
        if result.returncode:
            return result.returncode
        return 0
    finally:
        if server:
            server.shutdown(); server.server_close(); thread.join(timeout=3)
        fx.cleanup()


if __name__=='__main__':
    raise SystemExit(main())
