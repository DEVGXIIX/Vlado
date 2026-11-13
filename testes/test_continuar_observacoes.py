"""Selected human feedback reaches all stages, preserving sources and case scope."""
import copy
import unittest

import test_codex_integracao as fixture
from agente_fluxo_fixture import completar, esperar
from comum import ler_json, sha256
from cadastrar_documentos import cadastrar
from codex_apuracao import Conversas
import revisao_humana


class ContinuarObservacoesTest(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.CodexIntegrationTest(); self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.manager, self.root = self.fx.manager, self.fx.root
        self.chat = self.fx.start(); completar(self.manager, self.chat)
        self.first = self.manager.contexts[self.chat]['run']
        detail = revisao_humana.detalhe(self.root, 'alpha', 'R001', 'r3_sintese', 'g1', 'A001')
        saved = revisao_humana.salvar(self.root, 'alpha', 'R001', 'r3_sintese', achado_id='A001',
            achado_versao=1, registros_sha256=detail['registros_sha256'], estado='precisa_de_ajuste',
            observacao='O valor é do contrato inteiro, não de uma parcela.')
        self.request = {'rodada':'R001', 'revisao':'r3_sintese', 'geracao_achados':'g1', 'selecoes':[{
            'achado_id':'A001', 'achado_versao':1, 'registros_sha256':detail['registros_sha256'],
            'evento_id':saved['revisao_humana']['evento_id']}]}

    def test_complemento_recebe_observacoes_em_seis_etapas_e_preserva_rodada_anterior(self):
        before = {p:sha256(p) for p in self.first.rglob('*') if p.is_file()}
        preview = self.manager.observacoes({'caso':'alpha', **self.request})
        self.assertEqual(preview['conversa'], self.chat)
        calls_before = len(self.manager.rpc.calls)
        self.fx.start(conversa=self.chat, observacoes_humanas=self.request)
        completar(self.manager, self.chat)
        inputs = [p['input'][0]['text'] for m,p in self.manager.rpc.calls[calls_before:] if m == 'turn/start']
        self.assertEqual(len(inputs),6)
        self.assertTrue(all('contrato inteiro' in text and 'Reabra as fontes na rodada atual' in text for text in inputs))
        run = self.root/'execucoes/alpha/R002'
        report = ler_json(run/'saidas/codex_execucao.json')
        receipt = ler_json(run/'saidas/observacoes_humanas_recebidas.json')
        self.assertEqual(receipt['rodada_origem'],'R001')
        self.assertEqual(receipt['rodada_destino'],'R002')
        self.assertEqual(receipt['observacoes'][0]['fontes'][0]['documento_id'],'D001')
        self.assertEqual(report['observacoes_humanas']['sha256'], sha256(run/'saidas/observacoes_humanas_recebidas.json'))
        self.assertEqual(report['conferencia_humana'],'nao_realizada')
        self.assertIn('retorno humano selecionado',report['contaminacao_conhecida'])
        self.assertEqual([d['id'] for d in self.manager.contexts[self.chat]['manifest']['documentos']],['D001'])
        self.assertTrue(all(sha256(p)==digest for p,digest in before.items()))
        self.assertEqual(len([e for e in self.manager.eventos(self.chat)['eventos'] if e['tipo']=='observacoes_humanas']),1)
        self.fx.start(conversa=self.chat)
        completar(self.manager,self.chat)
        next_report=ler_json(self.root/'execucoes/alpha/R003/saidas/codex_execucao.json')
        self.assertIsNone(next_report['observacoes_humanas'])
        self.assertTrue(next_report['retorno_humano_no_contexto'])
        self.assertFalse((self.root/'execucoes/alpha/R003/saidas/observacoes_humanas_recebidas.json').exists())

    def test_envio_recusa_alteracao_desde_a_previa_sem_criar_outra_rodada(self):
        self.manager.observacoes({'caso':'alpha',**self.request})
        choice=self.request['selecoes'][0]
        revisao_humana.salvar(self.root,'alpha','R001','r3_sintese',achado_id='A001',achado_versao=1,
            registros_sha256=choice['registros_sha256'],anterior=choice['evento_id'],
            estado='sem_suporte_suficiente',observacao='Nova avaliação.')
        with self.assertRaisesRegex(ValueError,'marcação mudou'):
            self.manager.perguntar({'caso':'alpha','conversa':self.chat,'pergunta':'Reexaminar.',
                                   'observacoes_humanas':self.request})
        self.assertFalse((self.root/'execucoes/alpha/R002').exists())

    def test_selecao_nao_pode_ser_enviada_em_outra_conversa_ou_caso(self):
        for chat in (None,'f'*32):
            with self.subTest(chat=chat), self.assertRaisesRegex(ValueError,'outra conversa'):
                self.manager.perguntar({'caso':'alpha','conversa':chat,'pergunta':'Reexaminar.',
                                       'observacoes_humanas':self.request})
        with self.assertRaises((ValueError,OSError)):
            self.manager.observacoes({'caso':'beta',**self.request})
        forged=copy.deepcopy(self.request); forged['selecoes'][0]['texto']='Aprovação inventada'
        with self.assertRaises(ValueError):
            self.manager.perguntar({'caso':'alpha','conversa':self.chat,'pergunta':'Reexaminar.',
                                   'observacoes_humanas':forged})
        self.assertEqual(self.manager.contexts[self.chat]['meta']['rodadas'],['R001'])

    def test_rodada_sem_conversa_abre_nova_sobre_corpus_original_mesmo_apos_novo_cadastro(self):
        (self.manager._path(self.chat)/'conversa.json').rename(self.manager._path(self.chat)/'metadados_guardados.json')
        extra=self.root/'adicional.txt'; extra.write_text('Documento novo fora do corpus anterior.',encoding='utf-8')
        cadastrar(self.root,'alpha',[extra])
        other=Conversas(self.root,fixture.FakeServer); self.addCleanup(other.close)
        preview=other.observacoes({'caso':'alpha',**self.request})
        self.assertIsNone(preview['conversa'])
        response=other.perguntar({'caso':'alpha','pergunta':'Reexaminar a observação selecionada.',
                                 'observacoes_humanas':self.request})
        identifier=response['conversa']
        esperar(lambda: other.contexts[identifier]['meta'].get('turn_id'))
        completar(other,identifier)
        self.assertEqual(other.contexts[identifier]['meta']['estado'],'concluido')
        documents=other.contexts[identifier]['manifest']['documentos']
        self.assertEqual(len(documents),1)
        self.assertEqual(ler_json(other.contexts[identifier]['run']/'registro.json')['complemento_de'],'R001')
