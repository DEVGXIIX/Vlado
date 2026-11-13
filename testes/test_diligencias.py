"""Follow-up ownership, response ingestion and explicit reexamination, using synthetic sources."""
import copy
import http.client
import json
import threading
import unittest
import uuid

import test_caderno as notebook_fixture
from agente_fluxo_fixture import completar
from test_continuar_documentos import completar_expansao
from cadastrar_documentos import cadastrar
from comum import sha256, ler_json
from interface_pesquisa import Servidor, DILIGENCIAS_OPERACOES
from registros_achados import carregar
import caderno
import diligencias


class DiligenciasTest(unittest.TestCase):
    def setUp(self):
        self.fx=notebook_fixture.CadernoTest();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.root,self.manager=self.fx.root,self.fx.manager
        self.note=caderno.salvar(self.root,self.fx.request())

    def create(self,**changes):
        return {'caso':'alpha','requisicao_id':uuid.uuid4().hex,'autor':'Editora A',
            'origem':{'tipo':'humana',**self.fx.choice(self.note)},'acao':'Solicitar ordem bancária',
            'responsavel':'Repórter B','prazo':'2026-12-10','observacao':'Pendência atribuída ao jornalista.',**changes}

    def update(self,item,**changes):
        return {'caso':'alpha','diligencia_id':item['id'],'anterior_sha256':item['sha256'],
            'requisicao_id':uuid.uuid4().hex,'autor':'Repórter B','acao':item['diligencia']['acao'],
            'responsavel':'Repórter B','prazo':None,'estado':'aguardando_resposta',
            'observacao':'Solicitação enviada pelo jornalista fora do sistema.',**changes}

    def response(self,item):
        source=self.root/'retorno.txt';source.write_text('Contrato adicional. Valor total 246.',encoding='utf-8')
        receipt=cadastrar(self.root,'alpha',[source],natureza='sinteticos')
        docs=caderno.documentos(self.root,'alpha');doc=docs['documentos'][-1]
        return {'caso':'alpha','diligencia_id':item['id'],'anterior_sha256':item['sha256'],
            'requisicao_id':uuid.uuid4().hex,'autor':'Editora C','observacao':'RESPOSTA_DILIGENCIA: conferir alcance e atribuição.',
            'origem_id':docs['origem_id'],'documentos':[{'documento_id':doc['documento_id'],'sha256':doc['sha256']}]},receipt

    def choice(self,item):return {'diligencia_id':item['id'],'sha256':item['sha256']}

    def test_diligencia_livre_preserva_historico_sem_inventar_fonte(self):
        item = diligencias.salvar(self.root, self.create(origem=None))
        self.assertEqual(item['diligencia']['origem']['identidade'], {'tipo': 'livre'})
        self.assertEqual(item['diligencia']['origem']['fontes'], [])
        updated = diligencias.salvar(self.root, self.update(item), 'atualizar')
        self.assertEqual(updated['diligencia']['origem'], item['diligencia']['origem'])
        self.assertEqual(len(updated['historico']), 2)
        self.assertEqual(diligencias.listar(self.root, 'alpha')['total'], 1)

    def test_assumir_estados_historico_preservado_idempotencia_e_conflito(self):
        before={p:sha256(p) for p in self.root.rglob('*') if p.is_file()}
        body=self.create();first=diligencias.salvar(self.root,body)
        self.assertEqual(first['diligencia']['estado'],'a_solicitar');self.assertIsNone(self.manager.rpc)
        self.assertEqual(diligencias.salvar(self.root,body)['sha256'],first['sha256'])
        update=self.update(first);second=diligencias.salvar(self.root,update,'atualizar')
        self.assertEqual(second['historico'][0]['diligencia']['responsavel'],'Repórter B')
        self.assertEqual(second['diligencia']['estado'],'aguardando_resposta')
        self.assertEqual(second['historico'][1]['anterior_sha256'],first['sha256'])
        self.assertEqual(diligencias.salvar(self.root,update,'atualizar')['sha256'],second['sha256'])
        with self.assertRaisesRegex(ValueError,'mudou'):diligencias.salvar(self.root,self.update(first),'atualizar')
        with self.assertRaisesRegex(ValueError,'tentativa'):diligencias.salvar(self.root,{**update,'responsavel':'Outra pessoa'},'atualizar')
        self.assertTrue(all(sha256(p)==digest for p,digest in before.items()))
        self.assertEqual(diligencias.listar(self.root,'alpha',estado='aguardando_resposta',responsavel='B')['total'],1)
        self.assertEqual(diligencias.listar(self.root,'beta')['total'],0)

    def test_resposta_cadastrada_vinculada_sem_resolucao_automatica(self):
        item=diligencias.salvar(self.root,self.create());body,receipt=self.response(item)
        result=diligencias.salvar(self.root,body,'responder')
        self.assertEqual(receipt['recebidos'],1);self.assertEqual(result['diligencia']['estado'],'resposta_recebida')
        self.assertEqual(result['diligencia']['respostas'][0]['documentos'][0]['documento_id'],'D002')
        self.assertEqual(diligencias.original_resposta(self.root,{'caso':'alpha',**self.choice(result),'resposta_indice':0,'documento_indice':0}).read_bytes(),(self.root/'retorno.txt').read_bytes())
        self.assertEqual(diligencias.salvar(self.root,body,'responder')['sha256'],result['sha256'])
        self.assertEqual(len(diligencias.detalhe(self.root,'alpha',item['id'])['diligencia']['respostas']),1)
        closed=diligencias.salvar(self.root,self.update(result,estado='concluida',observacao='Conferência humana declarada com limites.'),'atualizar')
        self.assertEqual(len(closed['historico']),3)
        self.assertFalse((self.root/'execucoes/alpha').exists())
        original=diligencias.original_resposta(self.root,{'caso':'alpha',**self.choice(closed),'resposta_indice':0,'documento_indice':0})
        original.write_text('Adulteração sintética',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'original mudou'):diligencias.listar(self.root,'alpha')

    def test_achado_ia_tem_identidade_congelada_sem_mudar_revisao_humana(self):
        chat=self.fx.fx.start();completar(self.manager,chat)
        data,manifest=carregar(self.root,'alpha','R001','r3_sintese')
        before={p:sha256(p) for p in (self.root/'execucoes/alpha/R001').rglob('*') if p.is_file()}
        origin={'tipo':'ia','rodada':'R001','revisao':'r3_sintese','registros_sha256':manifest['registros_sha256'],
            'achado_id':'A001','achado_versao':1}
        item=diligencias.salvar(self.root,self.create(origem=origin))
        self.assertEqual(item['diligencia']['origem']['autor'],'IA')
        for changes in ({'achado_versao':2},{'registros_sha256':'0'*64},{'achado_id':'A999'},{'rodada':'../beta'}):
            with self.assertRaises((ValueError,OSError)):diligencias.salvar(self.root,self.create(origem={**origin,**changes}))
        self.assertTrue(all(sha256(p)==digest for p,digest in before.items()))
        self.assertEqual(data['conferencias_humanas'],[])

    def test_invalidos_fora_do_caso_historico_adulterado_e_selecao_obsoleta(self):
        for changes in ({'autor':''},{'responsavel':''},{'prazo':'2026-02-30'},{'acao':''},{'arquivo':'../../fora'},
                        {'origem':{'tipo':'humana',**self.fx.choice(self.note),'caso':'beta'}}):
            with self.subTest(changes=changes),self.assertRaises((ValueError,OSError)):diligencias.salvar(self.root,self.create(**changes))
        item=diligencias.salvar(self.root,self.create())
        with self.assertRaises((ValueError,OSError)):diligencias.detalhe(self.root,'beta',item['id'])
        with self.assertRaises(ValueError):diligencias.selecionar(self.root,'alpha',[self.choice(item)]*2)
        second=diligencias.salvar(self.root,self.update(item),'atualizar')
        with self.assertRaisesRegex(ValueError,'mudou'):diligencias.selecionar(self.root,'alpha',[self.choice(item)])
        body,_=self.response(second)
        with self.assertRaises(ValueError):diligencias.salvar(self.root,{**body,'documentos':[{'documento_id':'D002','sha256':'0'*64}]},'responder')
        path=next((self.root/f'casos/alpha/diligencias/{item["id"]}').glob('00000001*'))
        raw=ler_json(path);raw['diligencia']['responsavel']='Alteração sem histórico';path.write_text(json.dumps(raw),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Histórico'):diligencias.listar(self.root,'alpha')

    def test_retomada_explicita_contexto_seis_etapas_e_evolucao_com_resposta(self):
        item=diligencias.salvar(self.root,self.create());choice=self.choice(item)
        preview=self.manager.caderno_previa({'caso':'alpha','selecoes':[choice]},diligencias)
        self.assertIsNone(self.manager.rpc);self.assertEqual(preview['conteudo']['diligencias'][0]['id'],item['id'])
        chat=self.fx.fx.start(diligencias=[choice]);completar(self.manager,chat)
        report=ler_json(self.manager.contexts[chat]['run']/'saidas/codex_execucao.json')
        self.assertEqual(report['diligencias_recebidas']['quantidade'],1)
        prompts=[p['input'][0]['text'] for method,p in self.manager.rpc.calls if method=='turn/start']
        self.assertEqual(len(prompts),6);self.assertTrue(all('Solicitar ordem bancária' in p and 'sem aprovação automática' in p for p in prompts))
        body,_=self.response(item);received=diligencias.salvar(self.root,body,'responder');choice=self.choice(received)
        with self.assertRaisesRegex(ValueError,'novos documentos'):self.manager.caderno_previa({'caso':'alpha','conversa':chat,'selecoes':[choice]},diligencias)
        update=self.manager.preparar_corpus({'caso':'alpha','conversa':chat})['solicitacao']
        self.fx.fx.start(conversa=chat,diligencias=[choice],atualizar_corpus=update);completar_expansao(self.manager,chat)
        ctx=self.manager.contexts[chat];report=ler_json(ctx['run']/'saidas/codex_execucao.json')
        self.assertEqual(len(report['etapas_validadas']),7)
        self.assertEqual(report['diligencias_recebidas']['sha256'],sha256(ctx['run']/'saidas/diligencias_recebidas.json'))
        prompts=[p['input'][0]['text'] for method,p in self.manager.rpc.calls if method=='turn/start']
        self.assertTrue(all('RESPOSTA_DILIGENCIA' in p for p in prompts[-7:]))
        self.assertEqual(diligencias.detalhe(self.root,'alpha',item['id'])['diligencia']['estado'],'resposta_recebida')
        self.fx.fx.start(conversa=chat);completar(self.manager,chat)
        self.assertIsNone(ctx['meta']['diligencias_recebidas']);self.assertTrue(ctx['meta']['retorno_humano_no_contexto'])

    def test_http_protecao_preview_e_download_somente_documento_da_resposta(self):
        server=Servidor(('127.0.0.1',0),self.root);server.conversas=self.manager
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(3)))
        def post(op,data,headers=None,binary=False):
            con=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
            h={'Content-Type':'application/json','Origin':server.origin,'X-Session-Token':server.token};h.update(headers or {})
            con.request('POST','/api/'+op,json.dumps(data),h);response=con.getresponse();status=response.status;raw=response.read();con.close()
            return status,raw if binary else json.loads(raw)
        for op in (*DILIGENCIAS_OPERACOES,'codex-diligencias-previa'):
            for headers in ({'X-Session-Token':'errado'},{'Origin':'https://fora.test'}):self.assertEqual(post(op,{'caso':'alpha'},headers)[0],403)
        status,item=post('diligencias-criar',self.create());self.assertEqual(status,200)
        body,_=self.response(item);status,item=post('diligencias-responder',body);self.assertEqual(status,200)
        request={'caso':'alpha',**self.choice(item),'resposta_indice':0,'documento_indice':0}
        status,raw=post('diligencias-original',request,binary=True);self.assertEqual(status,200);self.assertIn(b'246',raw)
        self.assertEqual(post('diligencias-original',{**request,'caso':'beta'})[0],400)
        self.assertEqual(post('codex-diligencias-previa',{'caso':'alpha','selecoes':[self.choice(item)]})[0],200)
        self.assertIsNone(self.manager.rpc)


if __name__=='__main__':unittest.main()
