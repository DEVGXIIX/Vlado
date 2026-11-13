"""Receipt diagnostics distinguish denied access from missing or changed data."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import comum
from cadastrar_documentos import cadastrar, inventario
import test_registros as fixtures


class PermissoesCadastroTest(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.RegistrosTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        result = cadastrar(self.root, 'alpha', [self.root / 'fonte.txt'],
                           novo=True, titulo='Fixture sintética de permissões', natureza='sinteticos')
        self.receipt = self.root / result['arquivo_recibo']

    def test_recibo_ausente_tem_diagnostico_proprio(self):
        self.receipt.unlink()
        with self.assertRaisesRegex(ValueError, 'Recibo de cadastro ausente:'):
            inventario(self.root, 'alpha')

    def test_recibo_alterado_tem_diagnostico_proprio(self):
        self.receipt.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Hash divergente: Recibo de cadastro'):
            inventario(self.root, 'alpha')

    def test_negacao_ao_consultar_arquivo_nao_vira_ausencia(self):
        original = Path.stat
        target = self.receipt

        def blocked(path, *args, **kwargs):
            if path == target:
                raise PermissionError('Fixture: acesso negado')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'stat', blocked):
            with self.assertRaisesRegex(ValueError, 'Acesso negado ao ler recibo de cadastro:'):
                inventario(self.root, 'alpha')

    def test_negacao_ao_ler_conteudo_nao_vira_hash_divergente(self):
        original = comum.sha256

        def blocked(path):
            if path == self.receipt:
                raise PermissionError('Fixture: acesso negado na leitura')
            return original(path)

        with patch.object(comum, 'sha256', blocked):
            with self.assertRaisesRegex(ValueError, 'Acesso negado ao ler recibo de cadastro:'):
                inventario(self.root, 'alpha')


if __name__ == '__main__':
    unittest.main()
