"""Actual PDF extraction via browser upload and retry, with synthetic PDFs only."""
import argparse
import base64
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

from test_interface_pesquisa import InterfaceTest
from test_extracao_cadastro_pdf import pdf_sintetico
from comum import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node', required=True)
    parser.add_argument('--saida', required=True)
    parser.add_argument('--chrome', default='')
    args = parser.parse_args()
    fixture = InterfaceTest()
    fixture.setUp()
    try:
        pdf = pdf_sintetico(fixture.root / 'envio.pdf', ['Texto sintetico recebido pelo navegador.'])
        upload = [{'nome': 'PDF pendente.pdf', 'base64': base64.b64encode(pdf.read_bytes()).decode()}]
        failure = {'estado': 'erro', 'paginas_pdf': None, 'paginas_com_texto': 0,
                   'paginas_sem_texto': [], 'paginas_com_erro': [], 'ocr': False,
                   'metodo': None, 'mensagem': 'pypdf indisponivel neste Python'}
        with patch('cadastrar_documentos.extrair_pdf', return_value=failure):
            for case in ('gamma', 'delta'):
                status, _, result = fixture.request('/api/cadastrar', fixture.upload(caso=case, titulo='PDFs pendentes ' + case, arquivos=upload))
                assert status == 200
        original = fixture.root / result['inventario']['documentos'][0]['arquivo']
        original_hash = sha256(original)
        config_hash = sha256(fixture.root / 'configuracao.json')
        env = {**os.environ, 'NODE_PATH': args.modulos_node}
        result = subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), fixture.server.origin,
                                 str(Path(args.saida).resolve()), args.chrome, str(pdf)], env=env)
        assert sha256(original) == original_hash
        assert sha256(fixture.root / 'configuracao.json') == config_hash
        assert not (fixture.root / 'execucoes/gamma').exists()
        assert not (fixture.root / 'execucoes/delta').exists()
        return result.returncode
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    raise SystemExit(main())
