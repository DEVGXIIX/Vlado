"""Synthetic PDF ingestion, provenance, failure and snapshot integration tests."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cadastrar_documentos as cadastro
from comum import escrever_json, ler_json, sha256
from criar_caso import criar_caso
from extrair_pdf import extrair_pdf
from indice_sqlite import cobertura, pesquisar, ler_passagem
from nova_rodada import criar_rodada
from selecionar_caso import selecionar
import test_registros as fixtures

HAS_PYPDF = importlib.util.find_spec('pypdf') is not None


def pdf_sintetico(path, pages=('Marcador exclusivo do PDF sintetico.', None), *, password=None):
    """Create an actual PDF with standard-font text and optional blank pages."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    font_ref = writer._add_object(font)
    for text in pages:
        page = writer.add_blank_page(width=300, height=300)
        if text is not None:
            page[NameObject('/Resources')] = DictionaryObject({
                NameObject('/Font'): DictionaryObject({NameObject('/F1'): font_ref})})
            stream = DecodedStreamObject()
            literal = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            stream.set_data(f'BT /F1 12 Tf 20 200 Td ({literal}) Tj ET'.encode('ascii'))
            page[NameObject('/Contents')] = writer._add_object(stream)
    if password:
        writer.encrypt(password)
    writer.write(path)
    return path


class ExtracaoCadastroPDFTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RegistrosTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        selecionar(self.root, None)

    def register(self, sources, **kwargs):
        return cadastro.cadastrar(self.root, 'alpha', sources, **kwargs)

    def start(self, sources):
        return self.register(sources, novo=True, titulo='PDF sintetico', natureza='sinteticos')

    def manifest(self):
        return ler_json(self.root / 'casos/alpha/manifesto.json')

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_pdf_preparado_no_cadastro_e_pesquisavel_com_pagina_e_original(self):
        source = pdf_sintetico(self.root / 'fonte.pdf')
        original = source.read_bytes()
        result = self.start([source, source])
        self.assertEqual((result['novos'], result['duplicados']), (1, 1))
        self.assertEqual(result['extracao_pdf_resumo']['processados_agora'], 1)
        doc = self.manifest()['documentos'][0]
        self.assertEqual(doc['paginas_pdf'], 2)
        self.assertEqual(doc['extracao_pdf']['paginas_sem_texto'], [2])
        self.assertEqual(doc['extracao_pdf']['estado'], 'parcial')
        derivative = doc['derivados'][0]
        self.assertEqual(derivative['origem_sha256'], doc['sha256'])
        self.assertEqual(sha256(self.root / derivative['arquivo']), derivative['sha256'])
        self.assertEqual((self.root / doc['arquivo']).read_bytes(), original)
        self.assertFalse((self.root / 'execucoes').exists())
        self.assertIsNone(ler_json(self.root / 'configuracao.json')['caso_ativo'])
        selecionar(self.root, 'alpha')
        run = criar_rodada(self.root, 'R001', 'Pergunta sintetica de localizacao.', indice=True)
        response = pesquisar(self.root, 'alpha', 'R001', 'exclusivo', pagina=1)
        hit = response['resultados'][0]
        self.assertEqual(hit['pagina_pdf'], 1)
        self.assertEqual((run / hit['original']).read_bytes(), original)
        context = ler_passagem(self.root, 'alpha', 'R001', hit['referencia'])
        self.assertIn('exclusivo', json.dumps(context, ensure_ascii=False))
        units = [u for f in cobertura(self.root, 'alpha', 'R001')['cobertura']['documentos'][0]['fontes'] for u in f['unidades']]
        self.assertTrue(any(u['pagina_pdf'] == 2 and u['estado'] == 'sem_texto' for u in units))
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'EXTRAIVEL')['retornados'], 0)

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_duplicata_preparada_nao_reextrai_nem_muda_versao_ou_aprovacao(self):
        source = pdf_sintetico(self.root / 'fonte.pdf', ['Texto completo sintetico.'])
        self.start([source])
        path = self.root / 'casos/alpha/manifesto.json'
        manifest = self.manifest()
        manifest['protocolo'] = {'piloto_estabilizado': True, 'teste_principal_autorizado': True}
        escrever_json(path, manifest)
        before = manifest['documentos']
        with patch.object(cadastro, 'extrair_pdf', side_effect=AssertionError('Nao repetir extracao')):
            result = self.register([source])
        self.assertEqual(result['corpus_id'], 'alpha_v1')
        self.assertEqual(self.manifest()['documentos'], before)
        self.assertTrue(self.manifest()['protocolo']['piloto_estabilizado'])

    def test_dependencia_ausente_preserva_original_e_explica_falha(self):
        source = self.root / 'sem_dependencia.pdf'
        source.write_bytes(b'Synthetic bytes to test missing dependency only.')
        with patch.dict(sys.modules, {'pypdf': None}):
            result = self.start([source])
        doc = self.manifest()['documentos'][0]
        self.assertEqual(doc['extracao_pdf']['estado'], 'erro')
        self.assertIn('pypdf indisponivel', doc['extracao_pdf']['mensagem'])
        self.assertEqual(doc['derivados'], [])
        self.assertEqual((self.root / doc['arquivo']).read_bytes(), source.read_bytes())
        self.assertEqual(result['extracao_pdf_resumo']['erro'], 1)

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_protegido_invalido_e_paginas_sem_texto_nao_somem_do_recibo(self):
        locked = pdf_sintetico(self.root / 'senha.pdf', ['Texto protegido.'], password='sintetica')
        blank = pdf_sintetico(self.root / 'digitalizado.pdf', [None])
        invalid = self.root / 'invalido.pdf'
        invalid.write_bytes(b'%PDF-1.4\nInvalid synthetic fixture.')
        image = self.root / 'imagem.png'
        image.write_bytes(b'Synthetic image placeholder: no OCR expected.')
        result = self.start([locked, blank, invalid, image])
        self.assertEqual(result['recebidos'], 4)
        self.assertEqual(result['extracao_pdf_resumo']['erro'], 2)
        self.assertEqual(result['extracao_pdf_resumo']['sem_texto'], 1)
        self.assertNotIn('extracao_pdf', self.manifest()['documentos'][3])
        self.assertEqual([d['extracao_pdf']['estado'] for d in self.manifest()['documentos'][:3]],
                         ['erro', 'sem_texto', 'erro'])
        self.assertEqual(len(result['arquivos']), 4)

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_erro_em_uma_pagina_tem_localizador_e_nao_indexa_aviso(self):
        source = pdf_sintetico(self.root / 'parcial.pdf')
        class Page:
            def __init__(self, value): self.value = value
            def extract_text(self):
                if isinstance(self.value, Exception): raise self.value
                return self.value
        class Reader:
            is_encrypted = False
            pages = [Page('Marcador recuperavel.'), Page(ValueError('Erro sintetico')), Page('')]
        with patch('pypdf.PdfReader', return_value=Reader()):
            result = self.start([source])
        info = result['arquivos'][0]['extracao_pdf']
        self.assertEqual(info['paginas_com_erro'][0]['pagina_pdf'], 2)
        self.assertEqual(info['estado'], 'parcial')
        selecionar(self.root, 'alpha')
        criar_rodada(self.root, 'R001', 'Pergunta sintetica de cobertura.', indice=True)
        report = cobertura(self.root, 'alpha', 'R001')['cobertura']
        units = [u for f in report['documentos'][0]['fontes'] for u in f['unidades']]
        self.assertTrue(any(u['pagina_pdf'] == 2 and u['estado'] == 'erro_leitura' for u in units))
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'EXTRACAO')['retornados'], 0)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R001', 'recuperavel')['retornados'], 1)

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_preparacao_de_caso_existente_versiona_derivados_sem_alterar_rodada(self):
        source = pdf_sintetico(self.root / 'legado.pdf', ['Marcador retroativo exclusivo.'])
        with patch.dict(sys.modules, {'pypdf': None}):
            self.start([source])
        # Simulate a pre-extraction manifest with no preparation metadata.
        path = self.root / 'casos/alpha/manifesto.json'
        manifest = self.manifest()
        manifest['documentos'][0].pop('extracao_pdf')
        manifest['protocolo']['piloto_estabilizado'] = True
        escrever_json(path, manifest)
        original = manifest['documentos'][0].copy()
        selecionar(self.root, 'alpha')
        old = criar_rodada(self.root, 'R001', 'Pergunta sintetica anterior.', indice=True)
        old_hashes = {p.relative_to(old): sha256(p) for p in old.rglob('*') if p.is_file()}
        result = cadastro.preparar_pdfs(self.root, 'alpha')
        self.assertEqual(result['corpus_id'], 'alpha_v2')
        self.assertEqual(result['operacao'], 'preparacao_pdfs_cadastrados')
        self.assertEqual(result['novos'], 0)
        self.assertEqual(result['arquivos'][0]['nome_recebido'], 'legado.pdf')
        doc = self.manifest()['documentos'][0]
        self.assertEqual((doc['id'], doc['arquivo'], doc['sha256']),
                         (original['id'], original['arquivo'], original['sha256']))
        self.assertFalse(self.manifest()['protocolo']['piloto_estabilizado'])
        self.assertEqual(old_hashes, {p.relative_to(old): sha256(p) for p in old.rglob('*') if p.is_file()})
        self.assertFalse((self.root / 'execucoes/alpha/R002').exists())
        self.assertEqual(cobertura(self.root, 'alpha', 'R001')['cobertura']['documentos_pesquisaveis'], 0)
        criar_rodada(self.root, 'R002', 'Pergunta sintetica posterior.', indice=True)
        self.assertEqual(pesquisar(self.root, 'alpha', 'R002', 'retroativo')['retornados'], 1)

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_cli_legada_tambem_prepara_pdf_com_recibo(self):
        source = pdf_sintetico(self.root / 'legado.pdf', ['Texto sintetico legado.'])
        criar_caso(self.root, 'alpha', 'Legado', [source], 'sinteticos')
        doc = self.manifest()['documentos'][0]
        self.assertEqual(doc['extracao_pdf']['estado'], 'extraido')
        self.assertEqual(len(doc['derivados']), 1)
        self.assertEqual(len(self.manifest()['registros_cadastro']), 1)

    def test_falha_de_gravacao_na_extracao_nao_publica_caso_parcial(self):
        source = self.root / 'pdf.pdf'
        source.write_bytes(b'Synthetic fixture for storage failure.')
        with patch.object(cadastro, 'extrair_pdf', side_effect=OSError('Disco sintetico cheio')):
            with self.assertRaises(OSError):
                self.start([source])
        self.assertFalse((self.root / 'casos/alpha').exists())
        self.assertFalse((self.root / 'casos/.cadastro.lock').exists())

    @unittest.skipUnless(HAS_PYPDF, 'Instalar requirements.txt para testar extracao real')
    def test_extracao_avulsa_nao_sobrescreve_e_preserva_origem(self):
        source = pdf_sintetico(self.root / 'fonte.pdf', ['Texto sintetico.'])
        target = self.root / 'texto.md'
        before = sha256(source)
        self.assertEqual(extrair_pdf(source, 'D001', target)['estado'], 'extraido')
        with self.assertRaises(FileExistsError):
            extrair_pdf(source, 'D001', target)
        self.assertEqual(sha256(source), before)


if __name__ == '__main__':
    unittest.main()
