"""Check dependency selection, including the Windows entry point, without a server."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ambiente import diagnostico


class AmbienteTest(unittest.TestCase):
    def test_python_que_inicia_sem_extrator_nao_e_considerado_pronto(self):
        with patch('ambiente.importlib.import_module', side_effect=ImportError('sem pypdf')):
            result = diagnostico()
        self.assertFalse(result['pronto'])
        self.assertFalse(result['extracao_pdf']['disponivel'])
        self.assertEqual(result['python'], sys.executable)

    @unittest.skipUnless(os.name == 'nt', 'Iniciador Windows')
    def test_iniciador_verifica_o_runtime_com_dependencias_sem_abrir_servidor(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['cmd.exe', '/d', '/c', 'call', 'Iniciar pesquisa.cmd', '--verificar-runtime'],
                                cwd=root, env={**os.environ, 'APURACAO_OCULTO': '1'},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        environment = json.loads(result.stdout)
        self.assertTrue(environment['pronto'])
        self.assertTrue(environment['extracao_pdf']['disponivel'])
        self.assertTrue(environment['sqlite_fts5'])
