"""Backup and restore of the pilot's data folders; no network."""
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import backup


class BackupTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'origem'
        for relativo, conteudo in {'casos/catalogo.json': '{"casos": []}', 'conversas/a/conversa.json': '{}',
                                   'execucoes/c/R001/registro.json': '{}', 'acesso/acesso.json': '{"convites": {}}',
                                   'ajustes/inferencia.json': '{}', 'segredos/chaves.json': '{"anthropic": "sk-ant-x"}'}.items():
            arquivo = self.root / relativo
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(conteudo, encoding='utf-8')

    def test_backup_restaura_dados_e_omite_chaves_por_padrao(self):
        arquivo = backup.criar(self.root, self.base / 'copias')
        self.assertTrue(arquivo.name.startswith('vlado-dados-') and arquivo.name.endswith('.tar.gz'))
        with tarfile.open(arquivo) as pacote:
            nomes = pacote.getnames()
        self.assertIn('conversas/a/conversa.json', nomes)
        self.assertIn('manifesto_backup.json', nomes)
        self.assertFalse(any(n.startswith('segredos') for n in nomes))
        destino = self.base / 'destino'
        backup.restaurar(destino, arquivo)
        self.assertEqual((destino / 'acesso/acesso.json').read_text(encoding='utf-8'), '{"convites": {}}')
        self.assertFalse((destino / 'segredos').exists())

    def test_backup_com_chaves_somente_quando_pedido(self):
        arquivo = backup.criar(self.root, self.base / 'copias', incluir_segredos=True)
        with tarfile.open(arquivo) as pacote:
            self.assertIn('segredos/chaves.json', pacote.getnames())

    def test_restaurar_recusa_sobrescrever_dados_existentes_sem_confirmacao(self):
        arquivo = backup.criar(self.root, self.base / 'copias')
        with self.assertRaisesRegex(ValueError, 'já contém dados'):
            backup.restaurar(self.root, arquivo)
        backup.restaurar(self.root, arquivo, substituir=True)

    def test_restaurar_recusa_caminhos_fora_das_pastas_de_dados(self):
        malicioso = self.base / 'malicioso.tar.gz'
        with tarfile.open(malicioso, 'w:gz') as pacote:
            for nome in ('../fora.txt', 'scripts/acesso.py', 'casos/../../fora.txt'):
                dados = b'x'
                info = tarfile.TarInfo(nome)
                info.size = len(dados)
                pacote.addfile(info, io.BytesIO(dados))
        with self.assertRaisesRegex(ValueError, 'fora das pastas de dados'):
            backup.restaurar(self.base / 'novo', malicioso)
        self.assertFalse((self.base / 'fora.txt').exists())


if __name__ == '__main__':
    unittest.main()
