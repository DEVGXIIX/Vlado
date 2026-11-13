"""Browser acceptance on synthetic cases; restarts only the isolated test service."""
import argparse
import os
from pathlib import Path
import subprocess
import threading

from fixture_achados import Ambiente
from interface_pesquisa import Servidor
from comum import sha256
import apuracao


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default='node'); parser.add_argument('--modulos-node', required=True)
    parser.add_argument('--saida', required=True)
    parser.add_argument('--chrome', default='')
    args = parser.parse_args()
    output = Path(args.saida).resolve(); output.mkdir(parents=True, exist_ok=True)
    fx = Ambiente()
    try:
        fx.completo(); fx.caso('beta')
        preserved = {p: sha256(p) for sub in ('entradas', 'saidas') for p in (fx.run() / sub).rglob('*') if p.is_file()}
        for phase in ('fluxo', 'reinicio'):
            server = Servidor(('127.0.0.1', 0), fx.root)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                result = subprocess.run([args.node, str(Path(__file__).with_suffix('.cjs')), server.origin,
                    str(output), phase, args.chrome], env={**os.environ, 'NODE_PATH': args.modulos_node}, timeout=150)
                if result.returncode:
                    return result.returncode
            finally:
                server.shutdown(); server.server_close(); thread.join(3)
        assert len(apuracao.listar(fx.root, 'alpha')['notas']) == 2
        assert not apuracao.listar(fx.root, 'beta')['notas']
        assert all(sha256(p) == digest for p, digest in preserved.items()), 'Fonte ou resposta original alterada.'
        return 0
    finally:
        fx.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
