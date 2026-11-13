"""Browser acceptance of explicit human marks using synthetic findings only."""
import argparse
import os
from pathlib import Path
import subprocess
import threading

from fixture_achados import Ambiente
from interface_pesquisa import Servidor
from test_codex_integracao import FakeServer
from comum import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node', required=True)
    parser.add_argument('--saida', required=True)
    parser.add_argument('--chrome', default='')
    args = parser.parse_args()
    fx = Ambiente(); server = None
    try:
        fx.completo(quantidade=12)
        before = {p: sha256(p) for p in fx.run().rglob('*') if p.is_file()}
        server = Servidor(('127.0.0.1', 0), fx.root); server.conversas.factory = FakeServer
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        result = subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), server.origin,
                                 str(Path(args.saida).resolve()), args.chrome],
                                env={**os.environ, 'NODE_PATH':args.modulos_node})
        assert before == {p:sha256(p) for p in before}, 'Originais da IA, snapshots e bancos devem permanecer intactos.'
        return result.returncode
    finally:
        if server:
            server.shutdown(); server.server_close(); thread.join(timeout=3)
        fx.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
