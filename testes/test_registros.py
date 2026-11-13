"""Infrastructure checks; these are not editorial generation experiments."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from comum import (PARTES, conferir_projeto, dentro, escrever_json, fluxo_esperado,
                   manifesto_prompts, sha256)
from nova_rodada import criar_rodada
from criar_caso import criar_caso
from selecionar_caso import selecionar


class RegistrosTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'prompts').mkdir()
        for name in PARTES:
            (self.root / 'prompts' / name).write_text('# Modulo de fixture\n', encoding='utf-8')
        (self.root / 'prompts' / 'FLUXO_COMPLETO.md').write_bytes(fluxo_esperado(self.root))
        escrever_json(self.root / 'prompts' / 'manifesto_prompts.json', manifesto_prompts(self.root))
        (self.root / 'AGENTS.md').write_text('Fixture tecnica sem corpus real.', encoding='utf-8')
        (self.root / 'fonte.txt').write_text('Documento sintetico de teste de integridade.', encoding='utf-8')
        escrever_json(self.root / 'configuracao.json', {
            'versao':'1.0.0', 'manifesto_ativo':'manifesto.json', 'maximo_documentos_inicial':20,
            'caso_ativo':'fixture',
        })
        escrever_json(self.root / 'manifesto.json', {'caso_id':'fixture','corpus_id':'fixture_sintetica',
            'protocolo':{'piloto_estabilizado':False,'teste_principal_autorizado':False}, 'documentos':[
            {'id':'S001','arquivo':'fonte.txt','sha256':sha256(self.root / 'fonte.txt')}
        ]})

    def test_recusa_saida_do_projeto(self):
        with self.assertRaises(ValueError):
            dentro(self.root, '../fora.txt')
        with self.assertRaises(ValueError):
            dentro(self.root, str(self.root / 'absoluto.txt'))

    def test_detecta_original_alterado(self):
        (self.root / 'fonte.txt').write_text('Alteracao de fixture', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Hash divergente'):
            conferir_projeto(self.root)

    def test_detecta_prompt_alterado(self):
        (self.root / 'prompts' / PARTES[0]).write_text('Alteracao de fixture', encoding='utf-8')
        with self.assertRaises(ValueError):
            conferir_projeto(self.root)

    def test_snapshot_independe_da_alteracao_posterior(self):
        run = criar_rodada(self.root, 'R001', 'Pergunta sintetica para testar armazenamento.')
        (self.root / 'fonte.txt').write_text('Alteracao posterior', encoding='utf-8')
        self.assertIn('Documento sintetico', (run / 'entradas' / 'fonte.txt').read_text(encoding='utf-8'))
        for record in json.loads((run / 'snapshot.json').read_text(encoding='utf-8')):
            self.assertEqual(sha256(run / record['arquivo']), record['sha256'])
        metadata = json.loads((run / 'registro.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['etapas_concluidas'], [])
        self.assertEqual(metadata['estado'], 'entradas_congeladas_sem_geracao')

    def test_nao_sobrescreve_rodada(self):
        criar_rodada(self.root, 'R001', 'Pergunta de fixture.')
        with self.assertRaises(FileExistsError):
            criar_rodada(self.root, 'R001', 'Outra pergunta de fixture.')

    def test_nao_aceita_pergunta_vazia_ou_id_invalido(self):
        with self.assertRaises(ValueError):
            criar_rodada(self.root, '../fora', 'Pergunta de fixture.')
        with self.assertRaises(ValueError):
            criar_rodada(self.root, 'R002', '  ')

    def test_bloqueia_principal_sem_piloto(self):
        with self.assertRaisesRegex(ValueError, 'piloto estabilizado'):
            criar_rodada(self.root, 'R002', 'Pergunta de fixture.', tipo='principal')
        self.assertFalse((self.root / 'execucoes' / 'fixture' / 'R002').exists())

    def test_inicio_generico_nao_cria_rodada(self):
        selecionar(self.root, None)
        self.assertEqual(conferir_projeto(self.root)['estado'], 'sem_caso_selecionado')
        with self.assertRaisesRegex(ValueError, 'Nenhum caso ativo'):
            criar_rodada(self.root, 'R001', 'Pergunta de fixture.')

    def test_cadastro_nao_ativa_automaticamente(self):
        selecionar(self.root, None)
        criar_caso(self.root,'alpha','Caso sintetico A',[self.root/'fonte.txt'],'sinteticos')
        config=json.loads((self.root/'configuracao.json').read_text(encoding='utf-8'))
        self.assertIsNone(config['caso_ativo'])

    def test_casos_com_r001_permanecem_separados(self):
        source_b=self.root/'outra.txt'
        source_b.write_text('Outro documento sintetico de integridade.',encoding='utf-8')
        criar_caso(self.root,'alpha','Caso sintetico A',[self.root/'fonte.txt'],'sinteticos')
        criar_caso(self.root,'beta','Caso sintetico B',[source_b],'sinteticos')
        selecionar(self.root,'alpha')
        run_a=criar_rodada(self.root,'R001','Pergunta sintetica A.')
        selecionar(self.root,'beta')
        run_b=criar_rodada(self.root,'R001','Pergunta sintetica B.')
        self.assertNotEqual(run_a,run_b)
        self.assertFalse((run_a/'entradas'/'casos'/'beta').exists())
        self.assertFalse((run_b/'entradas'/'casos'/'alpha').exists())
        self.assertEqual(run_a.parent.name,'alpha')
        self.assertEqual(run_b.parent.name,'beta')

    def test_recusa_duplicata_documental(self):
        with self.assertRaisesRegex(ValueError,'identicos'):
            criar_caso(self.root,'alpha','Fixture',[self.root/'fonte.txt',self.root/'fonte.txt'])

    def test_caso_nao_sobrescrito(self):
        criar_caso(self.root,'alpha','Fixture',[self.root/'fonte.txt'])
        with self.assertRaises(FileExistsError):
            criar_caso(self.root,'alpha','Fixture',[self.root/'fonte.txt'])

    def test_caso_id_recusa_travessia(self):
        with self.assertRaises(ValueError):
            criar_caso(self.root,'../outro','Fixture',[self.root/'fonte.txt'])


if __name__ == '__main__':
    unittest.main()
