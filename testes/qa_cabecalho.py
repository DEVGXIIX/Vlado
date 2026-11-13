"""Check the header under the real CSP, with an isolated synthetic case."""
import argparse
import os
from pathlib import Path
import subprocess
import threading

from fixture_achados import Ambiente
from interface_pesquisa import Servidor
from test_codex_integracao import FakeServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', required=True)
    args = parser.parse_args()
    output = Path(args.saida).resolve()
    output.mkdir(parents=True, exist_ok=True)
    fixture = Ambiente()
    server = None
    try:
        server = Servidor(('127.0.0.1', 0), fixture.root)
        server.conversas.factory = FakeServer
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')),
                               server.origin, str(output)], env=os.environ.copy()).returncode
    finally:
        if server:
            server.shutdown()
            server.server_close()
        fixture.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
