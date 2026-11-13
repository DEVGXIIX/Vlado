"""Rebuildable findings index, read-only identity and complete filtered export."""
import copy
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from comum import sha256
from fixture_achados import Ambiente
from registros_achados import publicar
from indice_achados import construir, consultar, verificar, evidencia, detalhe, catalogo


class IndiceAchadosTest(unittest.TestCase):
    def setUp(self):
        self.fx=Ambiente()
        self.addCleanup(self.fx.cleanup)
        self.root,self.run=self.fx.root,self.fx.run()

    def test_reconstrucao_busca_historico_filtros_paginacao_exportacao(self):
        before=sha256(self.run/'indice/v1/apuracao.sqlite')
        initial,revised,_,_=self.fx.completo()
        construir(self.root,'alpha','R001','r2','g3')
        query=lambda **kw:consultar(self.root,'alpha','R001','r2','g2',**kw)
        result=query(limite=1)
        self.assertEqual(result['total_correspondencias'],2)
        self.assertEqual(result['proximo_deslocamento'],1)
        self.assertTrue(result['truncado'])
        self.assertEqual(query(limite=1,deslocamento=1)['resultados'][0]['id'],'A002')
        full=query(limite=1,deslocamento=1,completa=True)
        self.assertEqual(full['retornados'],2)
        self.assertFalse(full['truncado'])
        self.assertEqual(full['escopo_exportacao'],'selecao_filtrada_inteira')
        cases=[({'texto':'atribuição'},1),({'documento':'D002'},1),({'natureza':'pendencia'},1),
               ({'suporte':'sustentado'},1),({'humana':'retorno_recebido'},0),({'briefing':'sim'},1),
               ({'briefing':'nao'},1),({'destino':'retirado'},0),({'texto':"' OR 1=1 --"},0)]
        for filters,count in cases:
            with self.subTest(filters=filters):
                self.assertEqual(query(filtros=filters)['total_correspondencias'],count)
        detail=detalhe(self.root,'alpha','R001','r2','g2','A001')['achado']
        self.assertEqual(len(detail['historico']['versoes']),2)
        self.assertEqual(len(detail['evidencias']),3)
        self.assertEqual(detail['conferencia_humana'],'nao_realizada')
        self.assertEqual(query()['resultados'],consultar(self.root,'alpha','R001','r2','g3')['resultados'])
        self.assertEqual(sha256(self.run/'indice/v1/apuracao.sqlite'),before)
        self.assertEqual(verificar(self.root,'alpha','R001','r2','g2')['estado'],'valido')

    def test_rodada_antiga_indice_ausente_vazio_e_somente_pendencias(self):
        self.assertEqual(catalogo(self.root,'alpha','R001')['estado'],'nao_produzidos')
        data=self.fx.dados()
        data['achados']=data['achados'][1:]; data['vinculos']=[]
        self.fx.sincronizar_brutos(data)
        publicar(self.root,'alpha','R001',data)
        with self.assertRaisesRegex(ValueError,'ausente'):
            consultar(self.root,'alpha','R001','r1','g1')
        construir(self.root,'alpha','R001','r1','g1')
        self.assertEqual(consultar(self.root,'alpha','R001','r1','g1')['estado'],'somente_pendencias')
        self.fx.caso('beta',indice=False)
        empty=self.fx.dados('beta',indexed=False)
        self.fx.vazio_revisado(empty)
        publicar(self.root,'beta','R001',empty)
        construir(self.root,'beta','R001','r2','g1')
        self.assertEqual(consultar(self.root,'beta','R001','r2','g1')['estado'],'sem_achados_apos_revisao')

    def test_banco_divergente_outro_caso_revisao_e_fontes_ausentes(self):
        self.fx.completo()
        with self.assertRaisesRegex(ValueError,'divergente'):
            consultar(self.root,'alpha','R001','r1','g2')
        self.fx.caso('beta')
        data=self.fx.dados('beta'); publicar(self.root,'beta','R001',data)
        construir(self.root,'beta','R001','r1','g1')
        from shutil import copyfile
        copyfile(self.run/'saidas/achados/indices/g1/achados.sqlite',self.fx.run('beta')/'saidas/achados/indices/g1/achados.sqlite')
        with self.assertRaisesRegex(ValueError,'hash'):
            consultar(self.root,'beta','R001','r1','g1')
        path=self.run/'saidas/achados/indices/g2/achados.sqlite'
        with path.open('ab') as stream:
            stream.write(b'divergente')
        with self.assertRaisesRegex(ValueError,'hash'):
            consultar(self.root,'alpha','R001','r2','g2')
        source=self.fx.dados()['evidencias'][2]['original']
        (self.run/source).unlink()
        with self.assertRaises(ValueError):
            evidencia(self.root,'alpha','R001','r2','E003')

    def test_falha_indexacao_recibo_e_preservacao_canonica(self):
        publicar(self.root,'alpha','R001',self.fx.dados())
        with patch('indice_achados._verificar',side_effect=ValueError('Falha de integridade sintética')):
            with self.assertRaises(ValueError):
                construir(self.root,'alpha','R001','r1','g1')
        self.assertTrue((self.run/'saidas/achados/revisoes/r1/registros.json').is_file())
        self.assertFalse((self.run/'saidas/achados/indices/g1').exists())
        import json
        receipts=[json.loads(p.read_text(encoding='utf-8')) for p in (self.run/'saidas/achados/operacoes').glob('*.json')]
        self.assertTrue(any(r.get('estado')=='falha' and r.get('registros_preservados') for r in receipts))
        construir(self.root,'alpha','R001','r1','g1')
        with self.assertRaises(FileExistsError):
            construir(self.root,'alpha','R001','r1','g1')

    def test_visual_original_sem_fts_contexto_e_filtros_invalidos(self):
        self.fx.completo()
        result=evidencia(self.root,'alpha','R001','r2','E003')
        self.assertIsNone(result['contexto'])
        self.assertTrue((self.run/result['evidencia']['original']).is_file())
        self.assertEqual(len(evidencia(self.root,'alpha','R001','r2','E001')['contexto']),3)
        for kwargs in ({'filtros':[]},{'filtros':{'suporte':'sim'}},{'filtros':{'sql':'1=1'}},
                       {'filtros':{'texto':{}}},{'limite':True},{'deslocamento':-1},{'completa':'sim'}):
            with self.assertRaises(ValueError):
                consultar(self.root,'alpha','R001','r2','g2',**kwargs)
        with self.assertRaises(ValueError):
            evidencia(self.root,'alpha','R001','r2','E999')

    def test_cli_portavel_de_registro_a_exportacao(self):
        import json
        import shutil
        import subprocess
        project=Path(__file__).resolve().parents[1]
        shutil.copytree(project/'scripts',self.root/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
        (self.root/'modelos').mkdir()
        shutil.copyfile(project/'modelos/ACHADOS.schema.json',self.root/'modelos/ACHADOS.schema.json')
        candidate=self.root/'candidato.json'
        candidate.write_text(json.dumps(self.fx.dados(),ensure_ascii=False),encoding='utf-8')
        def call(operation,*args):
            result=subprocess.run([sys.executable,str(self.root/'scripts/achados.py'),operation,
                '--caso','alpha','--rodada','R001',*args],cwd=self.root,capture_output=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        self.assertEqual(call('validar','--arquivo','candidato.json')['estado'],'valido')
        self.assertEqual(call('registrar','--arquivo','candidato.json')['estado'],'publicado_sem_indice')
        self.assertEqual(call('listar')['revisoes'],['r1'])
        selectors=('--revisao','r1','--geracao','g1')
        call('construir',*selectors); call('verificar',*selectors)
        self.assertEqual(call('buscar',*selectors,'--natureza','pendencia')['total_correspondencias'],1)
        self.assertEqual(call('detalhe',*selectors,'--achado-id','A001')['achado']['id'],'A001')
        self.assertIsNone(call('evidencia','--revisao','r1','--evidencia-id','E003')['contexto'])
        self.assertEqual(call('exportar',*selectors,'--limite','1')['retornados'],2)


if __name__=='__main__':
    unittest.main()
