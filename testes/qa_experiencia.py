"""Browser acceptance using temporary synthetic documents; never starts inference."""
import os
from pathlib import Path
import subprocess
import threading
from fixture_achados import Ambiente
from criar_caso import criar_caso
from interface_pesquisa import Servidor


def main():
    fx = Ambiente()
    server = None
    try:
        fx.completo(quantidade=4)
        criar_caso(fx.root, 'beta', 'Pauta sem análise', [fx.text], 'sinteticos')
        server = Servidor(('127.0.0.1', 0), fx.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), server.origin],
                              env=os.environ.copy(), check=False).returncode
    finally:
        if server:
            server.shutdown()
            server.server_close()
        fx.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
