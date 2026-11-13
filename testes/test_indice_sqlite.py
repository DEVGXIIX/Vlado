"""Synthetic technical fixtures only; no editorial pilot or real corpus."""
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from comum import PARTES, escrever_json, fluxo_esperado, manifesto_prompts, sha256
from criar_caso import criar_caso
from selecionar_caso import selecionar
from nova_rodada import criar_rodada
from indice_sqlite import (construir_indice, pesquisar, ler_passagem, cobertura,
                           verificar_indice, _validar_banco)


class IndiceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'prompts').mkdir()
        for name in PARTES:
            (self.root / 'prompts' / name).write_text('# Fixture sintetica\n', encoding='utf-8')
        (self.root / 'prompts' / 'FLUXO_COMPLETO.md').write_bytes(fluxo_esperado(self.root))
        escrever_json(self.root / 'prompts' / 'manifesto_prompts.json', manifesto_prompts(self.root))
        (self.root / 'AGENTS.md').write_text('Fixture tecnica.', encoding='utf-8')
        escrever_json(self.root / 'configuracao.json', {'versao': '1.1.0', 'caso_ativo': None,
            'manifesto_ativo': None, 'maximo_documentos_inicial': 20, 'indice_sqlite': True})

    def caso(self, name='alpha', content='Ação técnica sintética. Código AB-123/2026.\nSegunda linha.\n'):
        path = self.root / f'{name}.txt'
        path.write_text(content, encoding='utf-8')
        criar_caso(self.root, name, 'Caso sintetico ' + name, [path], 'sinteticos')
        selecionar(self.root, name)
        return self.root / 'casos' / name / 'manifesto.json'

    def rodada(self, case='alpha', identifier='R001', **kwargs):
        selecionar(self.root, case)
        return criar_rodada(self.root, identifier, 'Pergunta sintetica de armazenamento, sem apuracao.', **kwargs)

    def test_busca_integrada_localizador_contexto_e_log(self):
        self.caso()
        run = self.rodada()
        response = pesquisar(self.root, 'alpha', 'R001', 'acao')
        self.assertEqual(response['total_correspondencias'], 1)
        hit = response['resultados'][0]
        self.assertIsNone(hit['pagina_pdf'])
        self.assertEqual(hit['linha_inicio'], 1)
        self.assertIn('Ação técnica', hit['trecho'])
        self.assertEqual(json.loads((run / response['arquivo_log']).read_text(encoding='utf-8')), response)
        read = ler_passagem(self.root, 'alpha', 'R001', hit['referencia'])
        self.assertEqual(read['unidade_completa'][1], {'linha': 2, 'texto': 'Segunda linha.'})
        self.assertTrue((run / hit['original']).is_file())
        self.assertEqual(sha256(run / hit['original']), hit['original_sha256'])
        self.assertEqual(verificar_indice(self.root, 'alpha', 'R001')['estado'], 'ok')

    def test_mesmos_ids_casos_distintos_e_troca_de_banco_rejeitada(self):
        self.caso('alpha', 'Marcador exclusivo alfabeto.\n')
        a = self.rodada('alpha')
        self.caso('beta', 'Marcador exclusivo betabetico.\n')
        b = self.rodada('beta')
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'betabetico')['total_correspondencias'], 0)
        self.assertEqual(pesquisar(self.root, 'beta', 'R001', 'alfabeto')['total_correspondencias'], 0)
        shutil.copyfile(a/'indice/v1/apuracao.sqlite', b/'indice/v1/apuracao.sqlite')
        shutil.copyfile(a/'indice/v1/manifesto.json', b/'indice/v1/manifesto.json')
        with self.assertRaisesRegex(ValueError, 'outro caso/rodada'):
            pesquisar(self.root, 'beta', 'R001', 'alfabeto')

    def test_mudanca_do_corpus_nao_altera_rodada_antiga(self):
        manifest_path = self.caso(content='Versão antiga sintética.\n')
        self.rodada()
        before = pesquisar(self.root, 'alpha', 'R001', 'antiga')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        path = self.root / manifest['documentos'][0]['arquivo']
        path.write_text('Versão nova sintética.\n', encoding='utf-8')
        manifest['documentos'][0]['sha256'] = sha256(path)
        manifest['corpus_id'] = 'alpha_v2'
        escrever_json(manifest_path, manifest)
        self.rodada(identifier='R002')
        after = pesquisar(self.root, 'alpha', 'R001', 'antiga')
        self.assertEqual(before['resultados'], after['resultados'])
        self.assertEqual(before['indice_id'], after['indice_id'])
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'nova')['total_correspondencias'], 0)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R002', 'nova')['total_correspondencias'], 1)

    def test_hash_divergente_no_snapshot_recusado(self):
        self.caso()
        run = self.rodada()
        hit = pesquisar(self.root, 'alpha', 'R001', 'acao')['resultados'][0]
        (run / hit['original']).write_text('Mudança indevida.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'hash divergente'):
            pesquisar(self.root, 'alpha', 'R001', 'acao')

    def test_banco_alterado_detectado(self):
        self.caso()
        run = self.rodada()
        with (run / 'indice/v1/apuracao.sqlite').open('ab') as stream:
            stream.write(b'tamper')
        with self.assertRaisesRegex(ValueError, 'Hash do banco'):
            verificar_indice(self.root, 'alpha', 'R001')

    def test_sem_indice_nao_cria_banco_na_busca(self):
        self.caso()
        run = self.rodada(indice=False)
        with self.assertRaisesRegex(ValueError, 'Indice inexistente'):
            pesquisar(self.root, 'alpha', 'R001', 'acao')
        self.assertFalse((run / 'indice').exists())
        construir_indice(self.root, 'alpha', 'R001')
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'acao')['total_correspondencias'], 1)

    def test_nova_geracao_reconstroi_sem_sobrescrever(self):
        self.caso()
        run = self.rodada()
        before = sha256(run / 'indice/v1/apuracao.sqlite')
        with self.assertRaises(FileExistsError):
            construir_indice(self.root, 'alpha', 'R001')
        a = pesquisar(self.root, 'alpha', 'R001', 'acao')
        construir_indice(self.root, 'alpha', 'R001', 'v2')
        b = pesquisar(self.root, 'alpha', 'R001', 'acao', geracao='v2')
        self.assertEqual(a['resultados'], b['resultados'])
        self.assertEqual(a['indice_id'], b['indice_id'])
        self.assertEqual(before, sha256(run / 'indice/v1/apuracao.sqlite'))

    def test_ausencia_consulta_invalida_e_sql_nao_executado(self):
        self.caso()
        run = self.rodada()
        empty = pesquisar(self.root, 'alpha', 'R001', 'inexistente')
        self.assertEqual(empty['total_correspondencias'], 0)
        self.assertTrue((run / empty['arquivo_log']).exists())
        for query, mode in [('', 'comum'), ('"aberta', 'comum'), ('NEAR(', 'fts')]:
            response = pesquisar(self.root, 'alpha', 'R001', query, modo=mode)
            self.assertEqual(response['estado'], 'erro_consulta')
            self.assertTrue((run / response['arquivo_log']).exists())
        response = pesquisar(self.root, 'alpha', 'R001', "'; DROP TABLE documentos; --", modo='literal')
        self.assertEqual(response['total_correspondencias'], 0)
        self.assertEqual(verificar_indice(self.root, 'alpha', 'R001')['estado'], 'ok')

    def test_frases_fts_e_literal_com_pontuacao(self):
        self.caso()
        self.rodada()
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', '"ação técnica"')['total_correspondencias'], 1)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'tecn* OR inexistente', modo='fts')['total_correspondencias'], 1)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'AB-123/2026', modo='literal')['total_correspondencias'], 1)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'AB/123/2026', modo='literal')['total_correspondencias'], 0)

    def test_truncamento_paginacao_filtros_e_blocos_sobrepostos(self):
        self.caso(content='\n'.join(f'Linha {i} marcador.' for i in range(100)))
        self.rodada()
        first = pesquisar(self.root, 'alpha', 'R001', 'marcador', limite=1, documentos=['D001'])
        self.assertEqual(first['total_correspondencias'], 3)
        self.assertTrue(first['truncado'])
        second = pesquisar(self.root, 'alpha', 'R001', 'marcador', limite=1, deslocamento=first['proximo_deslocamento'])
        self.assertNotEqual(first['resultados'][0]['referencia'], second['resultados'][0]['referencia'])
        invalid = pesquisar(self.root, 'alpha', 'R001', 'marcador', documentos=['D999'])
        self.assertEqual(invalid['estado'], 'erro_consulta')
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'marcador', pagina=1)['total_correspondencias'], 0)

    def _pdf_sintetico(self, *, bad_hash=False, bad_page=False):
        # This is a dummy byte fixture; neither a real PDF nor a PDF-reading test.
        source = self.root / 'fixture.pdf'
        source.write_bytes(b'Synthetic PDF placeholder for hash/adapter tests only.')
        criar_caso(self.root, 'alpha', 'Fixture sintetica paginada', [source], 'sinteticos')
        path = self.root / 'casos/alpha/manifesto.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        document = manifest['documentos'][0]
        text = self.root / 'casos/alpha/derivados/paginas.md'
        text.parent.mkdir()
        text.write_text('# D001 - copia textual de trabalho\n\n'
            'Original: fixture.pdf\n'
            f"SHA-256 do PDF: {'0'*64 if bad_hash else document['sha256']}\n"
            'Metodo: fixture sintetica; sem extracao real de PDF.\n'
            '## D001 - pagina PDF 1\n\n[L0001] Marcador paginado exclusivo.\n[L0002] Contexto adicional.\n\n'
            f"## D001 - pagina PDF {3 if bad_page else 2}\n\n[SEM TEXTO EXTRAIVEL NESTA PAGINA]\n", encoding='utf-8')
        document['derivados'] = [{'arquivo': 'casos/alpha/derivados/paginas.md', 'sha256': sha256(text)}]
        escrever_json(path, manifest)
        selecionar(self.root, 'alpha')

    def test_pagina_vazia_metadados_excluidos_e_localizador_pdf(self):
        self._pdf_sintetico()
        self.rodada()
        response = pesquisar(self.root, 'alpha', 'R001', 'paginado', pagina=1)
        self.assertEqual(response['total_correspondencias'], 1)
        hit = response['resultados'][0]
        self.assertEqual(hit['pagina_pdf'], 1)
        self.assertEqual(hit['linha_fim'], 2)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'Metodo')['total_correspondencias'], 0)
        report = cobertura(self.root, 'alpha', 'R001')['cobertura']
        units = [u for f in report['documentos'][0]['fontes'] for u in f['unidades']]
        self.assertTrue(any(u['pagina_pdf'] == 2 and u['estado'] == 'sem_texto' for u in units))
        self.assertTrue(any(u['estado'] == 'nao_suportado' for u in units))

    def test_derivado_com_origem_divergente_fica_sem_cobertura(self):
        self._pdf_sintetico(bad_hash=True)
        self.rodada()
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'paginado')['total_correspondencias'], 0)
        sources = cobertura(self.root, 'alpha', 'R001')['cobertura']['documentos'][0]['fontes']
        self.assertTrue(any(u['estado'] == 'erro_leitura' for f in sources for u in f['unidades']))

    def test_paginas_fora_de_sequencia_nao_ganham_localizador_inventado(self):
        self._pdf_sintetico(bad_page=True)
        self.rodada()
        self.assertEqual(cobertura(self.root, 'alpha', 'R001')['cobertura']['documentos_pesquisaveis'], 0)

    def test_utf8_invalido_e_texto_vazio_tem_cobertura_explicita(self):
        self.caso(content='')
        path = self.root / 'casos/alpha/manifesto.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        document = manifest['documentos'][0]
        binary = self.root / 'casos/alpha/derivado.txt'
        binary.write_bytes(b'\xff\xfe\xff')
        document['derivados'] = [{'arquivo': 'casos/alpha/derivado.txt', 'sha256': sha256(binary)}]
        escrever_json(path, manifest)
        self.rodada()
        report = cobertura(self.root, 'alpha', 'R001')['cobertura']
        self.assertEqual(report['documentos_pesquisaveis'], 0)
        states = {u['estado'] for f in report['documentos'][0]['fontes'] for u in f['unidades']}
        self.assertEqual(states, {'sem_texto', 'erro_leitura'})

    def test_arquivo_de_outro_caso_no_manifesto_recusado(self):
        manifest_path = self.caso()
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        self.caso('beta', 'Outro marcador sintetico.\n')
        beta = json.loads((self.root/'casos/beta/manifesto.json').read_text(encoding='utf-8'))
        manifest['documentos'][0]['derivados'] = [beta['documentos'][0]]
        escrever_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, 'nao pertence ao caso'):
            self.rodada('alpha')
        self.assertFalse((self.root / 'execucoes/alpha/R001').exists())

    def test_falha_de_construcao_nao_publica_rodada_parcial(self):
        self.caso()
        with patch('indice_sqlite._adaptar', side_effect=RuntimeError('Falha sintetica')):
            with self.assertRaisesRegex(RuntimeError, 'Falha sintetica'):
                self.rodada()
        self.assertFalse((self.root / 'execucoes/alpha/R001').exists())
        self.assertEqual(list((self.root / 'execucoes/alpha').iterdir()), [])

    def test_verificacao_detecta_fts_divergente(self):
        self.caso()
        run = self.rodada()
        con = sqlite3.connect(run / 'indice/v1/apuracao.sqlite')
        self.addCleanup(con.close)
        con.execute('DELETE FROM trechos_fts')
        with self.assertRaisesRegex(ValueError, 'FTS e trechos'):
            _validar_banco(con)

    def test_ids_travessia_e_caminhos_invalidos(self):
        self.caso()
        self.rodada()
        for case, round_id, generation in [('../alpha', 'R001', 'v1'), ('alpha', '../R001', 'v1'), ('alpha','R001','../v1')]:
            with self.assertRaises(ValueError):
                pesquisar(self.root, case, round_id, 'acao', geracao=generation)

    def test_cli_em_copia_portavel_e_consulta_por_arquivo(self):
        self.caso()
        self.rodada()
        (self.root / 'scripts').mkdir()
        active_scripts = Path(__file__).resolve().parents[1] / 'scripts'
        for name in ('banco.py', 'indice_sqlite.py', 'comum.py'):
            shutil.copyfile(active_scripts / name, self.root / 'scripts' / name)
        (self.root / 'entrada').mkdir()
        (self.root / 'entrada/query.txt').write_text('acao', encoding='utf-8')
        script = self.root / 'scripts/banco.py'
        result = subprocess.run([sys.executable, str(script), 'buscar', '--caso', 'alpha', '--rodada', 'R001',
                                  '--consulta-arquivo', 'entrada/query.txt'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response['total_correspondencias'], 1)
        self.assertTrue((self.root/'execucoes/alpha/R001'/response['arquivo_log']).is_file())


if __name__ == '__main__':
    unittest.main()
