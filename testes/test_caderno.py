"""Human notebooks keep authors, source identities and model context explicit."""
import copy
import http.client
import json
import threading
import unittest
import uuid

import test_codex_integracao as fixture
import test_continuar_documentos as evolution_fixture
from agente_fluxo_fixture import completar
from cadastrar_documentos import cadastrar
from comum import sha256, ler_json
from interface_pesquisa import Servidor, CADERNO_OPERACOES
from indice_sqlite import pesquisar
import caderno


class CadernoTest(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.CodexIntegrationTest();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.root,self.manager=self.fx.root,self.fx.manager

    def request(self,**changes):
        docs=caderno.documentos(self.root,'alpha');doc=docs['documentos'][0]
        return {**{'caso':'alpha','origem_id':docs['origem_id'],'documento_id':doc['documento_id'],
            'documento_sha256':doc['sha256'],'pagina_pdf':None,'localizador':'Linha 1',
            'trecho':'Alfabeto sintético. Valor 123.','titulo':'Contribuição humana de teste',
            'anotacao':'HIPOTESE_JORNALISTA_X: interpretação humana para reexame.',
            'autor':'Repórter de teste','tipo':'achado','transcricao_manual':False,
            'requisicao_id':uuid.uuid4().hex},**changes}

    def choice(self,result):
        return {'registro_id':result['registro']['id'],'sha256':result['sha256']}

    def test_salvar_antes_da_pergunta_preserva_fontes_autoria_e_idempotencia(self):
        before={p:sha256(p) for p in self.root.rglob('*') if p.is_file()}
        body=self.request();saved=caderno.salvar(self.root,body)
        entry=saved['registro'];self.assertEqual(entry['autor'],'Repórter de teste')
        self.assertEqual(entry['origem_autoria'],'humana_declarada_na_interface')
        self.assertEqual(entry['fontes'][0]['conferencia_textual'],'literal_localizado')
        self.assertTrue(all(sha256(p)==digest for p,digest in before.items()))
        self.assertFalse((self.root/'execucoes/alpha').exists())
        self.assertIsNone(self.manager.rpc)
        self.assertEqual(caderno.salvar(self.root,body)['sha256'],saved['sha256'])
        self.assertEqual(caderno.listar(self.root,'alpha')['total'],1)
        with self.assertRaisesRegex(ValueError,'tentativa de salvamento'):
            caderno.salvar(self.root,{**body,'autor':'Outro nome'})
        self.assertEqual(caderno.detalhe(self.root,'alpha',entry['id'])['registro']['autor'],'Repórter de teste')
        self.assertEqual(caderno.original_registro(self.root,{'caso':'alpha',**self.choice(saved)}).read_bytes(),(self.root/'alpha.txt').read_bytes())

    def test_pdf_exige_pagina_fisica_valida_e_transcricao_manual_explicita(self):
        from pypdf import PdfWriter
        pdf=self.root/'scan.pdf';writer=PdfWriter();writer.add_blank_page(width=300,height=300);writer.write(pdf)
        cadastrar(self.root,'alpha',[pdf],natureza='sinteticos')
        docs=caderno.documentos(self.root,'alpha');doc=next(d for d in docs['documentos'] if d['formato']=='.pdf')
        body=self.request(origem_id=docs['origem_id'],documento_id=doc['documento_id'],documento_sha256=doc['sha256'],
            pagina_pdf=1,trecho='Transcrição visual sintética.',localizador='Carimbo no canto inferior')
        with self.assertRaisesRegex(ValueError,'transcrição manual'):caderno.salvar(self.root,body)
        saved=caderno.salvar(self.root,{**body,'transcricao_manual':True})
        self.assertEqual(saved['registro']['fontes'][0]['pagina_pdf'],1)
        self.assertEqual(saved['registro']['fontes'][0]['conferencia_textual'],'transcricao_humana')
        for page in (0,2,True):
            with self.subTest(page=page),self.assertRaisesRegex(ValueError,'página física'):
                caderno.salvar(self.root,{**body,'requisicao_id':uuid.uuid4().hex,'pagina_pdf':page,'transcricao_manual':True})

    def test_cruzamento_preserva_pais_fontes_autorias_e_paginacao(self):
        first=caderno.salvar(self.root,self.request(autor='Autora A',titulo='Nota A'))
        second=caderno.salvar(self.root,self.request(autor='Autor B',titulo='Nota B',trecho='<script>não executar</script>',localizador='Linha 2'))
        before={self.root/f'casos/alpha/caderno/registros/{item["registro"]["id"]}.json':item['sha256'] for item in (first,second)}
        cross=caderno.cruzar(self.root,{'caso':'alpha','selecoes':[self.choice(first),self.choice(second)],
            'titulo':'Cruzamento humano','anotacao':'Relação sugerida pela editora, sujeita a reexame.',
            'autor':'Editora C','requisicao_id':uuid.uuid4().hex})
        self.assertEqual(cross['registro']['tipo'],'cruzamento')
        self.assertEqual(cross['registro']['autor'],'Editora C')
        self.assertEqual([p['autor'] for p in cross['registro']['vinculos']],['Autora A','Autor B'])
        self.assertEqual(len(cross['registro']['fontes']),2)
        self.assertTrue(all(sha256(p)==digest for p,digest in before.items()))
        self.assertEqual(caderno.listar(self.root,'alpha',texto='Editora C')['total'],1)
        self.assertEqual(caderno.listar(self.root,'alpha',limite=1)['proximo_deslocamento'],1)
        with self.assertRaises(ValueError):caderno.selecionar(self.root,'alpha',[self.choice(first)]*2)

    def test_origens_sao_congeladas_e_identidades_ou_fontes_trocadas_sao_recusadas(self):
        body=self.request();saved=caderno.salvar(self.root,body)
        extra=self.root/'extra.txt';extra.write_text('Nova fonte sintética.',encoding='utf-8');cadastrar(self.root,'alpha',[extra])
        self.assertEqual(caderno.detalhe(self.root,'alpha',saved['registro']['id'])['sha256'],saved['sha256'])
        with self.assertRaisesRegex(ValueError,'inventário mudou'):
            caderno.salvar(self.root,{**body,'requisicao_id':uuid.uuid4().hex})
        for changes in ({'autor':''},{'documento_id':'../beta'},{'documento_sha256':'0'*64},
                        {'pagina_pdf':1},{'trecho':'Texto não presente'},{'original':'../fora'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):caderno.salvar(self.root,self.request(**changes))
        with self.assertRaises((ValueError,OSError)):caderno.selecionar(self.root,'beta',[self.choice(saved)])
        with self.assertRaises(ValueError):caderno.selecionar(self.root,'alpha',[{**self.choice(saved),'sha256':'0'*64}])
        original=caderno.original_registro(self.root,{'caso':'alpha',**self.choice(saved)})
        original.write_text('Fonte adulterada no teste.',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'original mudou'):caderno.listar(self.root,'alpha')

    def test_http_sessao_origem_original_e_autoria_identificada(self):
        server=Servidor(('127.0.0.1',0),self.root);server.conversas=self.manager
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(3)))
        def post(op,data,headers=None,binary=False):
            con=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
            h={'Content-Type':'application/json','Origin':server.origin,'X-Session-Token':server.token};h.update(headers or {})
            con.request('POST','/api/'+op,json.dumps(data),h);response=con.getresponse();status=response.status;raw=response.read();con.close()
            return status,raw if binary else json.loads(raw)
        for op in (*CADERNO_OPERACOES,'codex-caderno-previa'):
            for headers in ({'X-Session-Token':'errado'},{'Origin':'https://fora.test'}):
                self.assertEqual(post(op,{'caso':'alpha'},headers)[0],403)
        status,saved=post('caderno-salvar',self.request())
        self.assertEqual(status,200);self.assertEqual(saved['registro']['autor'],'Repórter de teste')
        status,content=post('caderno-original',{'caso':'alpha',**self.choice(saved)},binary=True)
        self.assertEqual(status,200);self.assertEqual(content,(self.root/'alpha.txt').read_bytes())
        status,preview=post('codex-caderno-previa',{'caso':'alpha','selecoes':[self.choice(saved)]})
        self.assertEqual(status,200);self.assertEqual(preview['conteudo']['registros'][0]['registro']['id'],saved['registro']['id'])
        self.assertIsNone(self.manager.rpc)

    def test_contexto_chega_as_etapas_com_autoria_sem_entrar_no_fts_ou_aprovar_ia(self):
        saved=caderno.salvar(self.root,self.request());choice=self.choice(saved)
        original_hash=saved['sha256'];chat=self.fx.start(registros_caderno=[choice]);completar(self.manager,chat)
        ctx=self.manager.contexts[chat];report=ler_json(ctx['run']/'saidas/codex_execucao.json')
        receipt=ler_json(ctx['run']/'saidas/caderno_recebido.json')
        self.assertEqual(receipt['registros'][0]['sha256'],original_hash)
        self.assertEqual(report['caderno_recebido']['sha256'],sha256(ctx['run']/'saidas/caderno_recebido.json'))
        prompts=[p['input'][0]['text'] for method,p in self.manager.rpc.calls if method=='turn/start']
        self.assertEqual(len(prompts),6)
        self.assertTrue(all('HIPOTESE_JORNALISTA_X' in p and 'Repórter de teste' in p and 'CADERNO HUMANO' in p for p in prompts))
        self.assertEqual(pesquisar(self.root,'alpha','R001','HIPOTESE_JORNALISTA_X')['total_correspondencias'],0)
        self.assertEqual(report['conferencia_humana'],'nao_realizada')
        self.assertEqual(len(ctx['manifest']['documentos']),1)
        self.assertEqual(caderno.detalhe(self.root,'alpha',saved['registro']['id'])['sha256'],original_hash)
        self.fx.start(conversa=chat);completar(self.manager,chat)
        next_report=ler_json(ctx['run']/'saidas/codex_execucao.json')
        self.assertIsNone(next_report['caderno_recebido']);self.assertTrue(next_report['retorno_humano_no_contexto'])

    def test_fonte_nova_nao_abrange_conversa_antiga_sem_atualizacao_explicita(self):
        chat=self.fx.start();completar(self.manager,chat)
        path=self.root/'novo.txt';path.write_text('Contrato adicional. Valor total 246.',encoding='utf-8');cadastrar(self.root,'alpha',[path])
        docs=caderno.documentos(self.root,'alpha');doc=docs['documentos'][-1]
        saved=caderno.salvar(self.root,self.request(documento_id=doc['documento_id'],documento_sha256=doc['sha256'],trecho='Contrato adicional. Valor total 246.'))
        choice=self.choice(saved)
        with self.assertRaisesRegex(ValueError,'versão desta conversa'):
            self.manager.caderno_previa({'caso':'alpha','conversa':chat,'selecoes':[choice]})
        with self.assertRaisesRegex(ValueError,'versão desta conversa'):
            self.manager.perguntar({'caso':'alpha','conversa':chat,'pergunta':'Reexaminar.','registros_caderno':[choice]})
        self.assertFalse((self.root/'execucoes/alpha/R002').exists())
        preview=self.manager.preparar_corpus({'caso':'alpha','conversa':chat})
        context=self.manager.caderno_previa({'caso':'alpha','conversa':chat,'selecoes':[choice],'atualizar_corpus':preview['solicitacao']})
        self.assertEqual(context['conteudo']['registros'][0]['registro']['autor'],'Repórter de teste')
        self.fx.start(conversa=chat,registros_caderno=[choice],atualizar_corpus=preview['solicitacao'])
        evolution_fixture.completar_expansao(self.manager,chat)
        self.assertEqual(self.manager.contexts[chat]['meta']['estado'],'concluido')
        self.assertIsNotNone(self.manager.contexts[chat]['meta']['caderno_recebido'])
