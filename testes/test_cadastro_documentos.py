"""Batch receipt/storage tests, using only temporary synthetic files."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cadastrar_documentos as cadastro
import test_registros as fixtures
from comum import escrever_json, ler_json, sha256
from nova_rodada import criar_rodada
from selecionar_caso import selecionar
from indice_sqlite import pesquisar
from criar_caso import criar_caso


class CadastroTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RegistrosTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        selecionar(self.root, None)
        self.first = self.root / 'fonte.txt'
        self.second = self.root / 'segunda.txt'
        self.second.write_text('Segunda fonte sintética exclusiva.', encoding='utf-8')

    def register(self, files=None, **kwargs):
        return cadastro.cadastrar(self.root, 'alpha', files or [self.first], **kwargs)

    def start(self, files=None):
        return self.register(files, novo=True, titulo='Caso sintético', natureza='sinteticos')

    def test_lote_pre_pergunta_contabiliza_todos_sem_ativar_ou_criar_rodada(self):
        duplicate = self.root / 'copia.txt'
        duplicate.write_bytes(self.first.read_bytes())
        result = self.start([self.first, self.second, duplicate])
        self.assertEqual((result['recebidos'], result['novos'], result['duplicados']), (3, 2, 1))
        self.assertEqual(len(result['arquivos']), 3)
        self.assertEqual([r['documento_id'] for r in result['arquivos']], ['D001', 'D002', 'D001'])
        self.assertIsNone(ler_json(self.root / 'configuracao.json')['caso_ativo'])
        self.assertFalse((self.root / 'execucoes').exists())
        self.assertEqual(ler_json(self.root / result['arquivo_recibo'])['recebidos'], 3)
        self.assertEqual(result['inventario']['total_documentos'], 2)

    def test_lotes_acumulados_preservam_ids_nomes_iguais_e_historico(self):
        before = self.start()
        manifest_before = (self.root / 'casos/alpha/manifesto.json').read_bytes()
        other = self.root / 'outro' / self.first.name
        other.parent.mkdir()
        other.write_text('Conteúdo novo com o mesmo nome de arquivo.', encoding='utf-8')
        result = self.register([other], natureza='sinteticos')
        self.assertEqual(result['total_documentos'], 2)
        self.assertEqual(result['corpus_id'], 'alpha_v2')
        docs = result['inventario']['documentos']
        self.assertEqual(docs[0]['id'], 'D001')
        self.assertEqual(docs[1]['id'], 'D002')
        self.assertEqual(docs[0]['nome_recebido'], docs[1]['nome_recebido'])
        self.assertNotEqual(docs[0]['arquivo'], docs[1]['arquivo'])
        history = (self.root / result['arquivo_recibo']).parent / 'manifesto_anterior.json'
        self.assertEqual(history.read_bytes(), manifest_before)
        self.assertTrue((self.root / before['arquivo_recibo']).is_file())

    def test_reenvio_so_duplicado_nao_altera_corpus_ou_aprovacao(self):
        self.start()
        path = self.root / 'casos/alpha/manifesto.json'
        manifest = ler_json(path)
        manifest['protocolo'] = {'piloto_estabilizado': True, 'teste_principal_autorizado': True}
        escrever_json(path, manifest)
        duplicate = self.register(natureza='sinteticos')
        self.assertEqual(duplicate['corpus_id'], 'alpha_v1')
        self.assertEqual(duplicate['novos'], 0)
        self.assertTrue(ler_json(path)['protocolo']['piloto_estabilizado'])
        self.register([self.second], natureza='sinteticos')
        self.assertFalse(ler_json(path)['protocolo']['piloto_estabilizado'])

    def test_formato_invalido_ou_limite_nao_publica_lote_parcial(self):
        self.start()
        path = self.root / 'casos/alpha/manifesto.json'
        before = path.read_bytes()
        invalid = self.root / 'invalido.exe'
        invalid.write_bytes(b'Synthetic only')
        with self.assertRaisesRegex(ValueError, 'Nenhum arquivo'):
            self.register([self.second, invalid])
        self.assertEqual(path.read_bytes(), before)
        config = ler_json(self.root / 'configuracao.json')
        config['maximo_documentos_inicial'] = 1
        escrever_json(self.root / 'configuracao.json', config)
        with self.assertRaisesRegex(ValueError, 'limite'):
            self.register([self.second])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(len(list((path.parent / 'cadastros').iterdir())), 1)

    def test_falha_de_publicacao_restaura_manifesto_catalogo_e_arquivos(self):
        self.start()
        path = self.root / 'casos/alpha/manifesto.json'
        before = path.read_bytes()
        cat_before = (self.root / 'casos/catalogo.json').read_bytes()
        original = cadastro._atomico
        failed = False

        def fail_once(target, data):
            nonlocal failed
            if target.name == 'catalogo.json' and not failed:
                failed = True
                raise OSError('Falha sintética de publicação')
            return original(target, data)

        with patch.object(cadastro, '_atomico', fail_once):
            with self.assertRaises(OSError):
                self.register([self.second])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual((self.root / 'casos/catalogo.json').read_bytes(), cat_before)
        self.assertEqual(len(list((path.parent / 'cadastros').iterdir())), 1)
        self.assertFalse((self.root / 'casos/.cadastro.lock').exists())

    def test_pergunta_congela_todos_documentos_e_recibos_sem_mudar_rodada_antiga(self):
        first = self.start()
        selecionar(self.root, 'alpha')
        run = criar_rodada(self.root, 'R001', 'Pergunta sintética para teste de snapshot.', indice=True)
        original = (run / 'snapshot.json').read_bytes()
        self.assertTrue((run / 'entradas' / first['arquivo_recibo']).is_file())
        self.register([self.second], natureza='sinteticos')
        self.assertEqual((run / 'snapshot.json').read_bytes(), original)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'exclusiva')['retornados'], 0)
        second_run = criar_rodada(self.root, 'R002', 'Outra pergunta sintética.', indice=True)
        manifest = ler_json(second_run / 'entradas/casos/alpha/manifesto.json')
        self.assertEqual(len(manifest['documentos']), 2)
        self.assertEqual(len(manifest['registros_cadastro']), 2)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R002', 'exclusiva')['retornados'], 1)

    def test_recibo_alterado_bloqueia_snapshot(self):
        result = self.start()
        selecionar(self.root, 'alpha')
        (self.root / result['arquivo_recibo']).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Recibo'):
            criar_rodada(self.root, 'R001', 'Pergunta sintética.')
        self.assertFalse((self.root / 'execucoes/alpha/R001').exists())

    def test_cadastro_concorrente_e_caso_inexistente_nao_misturam_acervos(self):
        self.start()
        lock = self.root / 'casos/.cadastro.lock'
        lock.mkdir()
        with self.assertRaisesRegex(ValueError, 'andamento'):
            self.register([self.second])
        with self.assertRaisesRegex(ValueError, 'andamento'):
            criar_rodada(self.root, 'R001', 'Pergunta sintética durante cadastro.')
        lock.rmdir()
        with self.assertRaisesRegex(ValueError, 'inexistente'):
            cadastro.cadastrar(self.root, 'beta', [self.second])
        with self.assertRaises(ValueError):
            cadastro.cadastrar(self.root, '../outro', [self.second])

    def test_caso_legado_versionado_recebe_lote_com_nova_versao(self):
        criar_caso(self.root, 'alpha', 'Legado sintético', [self.first], 'sinteticos')
        path = self.root / 'casos/alpha/manifesto.json'
        manifest = ler_json(path)
        manifest['corpus_id'] = 'alpha_v9'
        escrever_json(path, manifest)
        result = self.register([self.second], natureza='sinteticos')
        self.assertEqual(result['corpus_id'], 'alpha_v10')
        self.assertEqual(result['total_documentos'], 2)


if __name__ == '__main__':
    unittest.main()
