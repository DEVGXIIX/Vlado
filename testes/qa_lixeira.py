"""Browser acceptance of reversible exclusions; synthetic files, no inference."""
import argparse
import os
from pathlib import Path
import subprocess

from test_interface_pesquisa import InterfaceTest
from test_codex_integracao import FakeServer
from nova_rodada import criar_rodada


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modulos-node', required=True)
    parser.add_argument('--saida', required=True)
    parser.add_argument('--chrome', default='')
    args = parser.parse_args()
    fixture = InterfaceTest()
    fixture.setUp()
    try:
        criar_rodada(fixture.root, 'R002', 'Rodada sintética avulsa.', caso='alpha')
        fixture.conversa_sintetica()
        active = fixture.conversa_sintetica('b' * 32, 'beta', estado='executando')
        fixture.server.conversas.contexts[active['id']] = {'meta': active, 'busy': True, 'events': []}
        fixture.server.conversas.factory = FakeServer
        env = {**os.environ, 'NODE_PATH': args.modulos_node}
        return subprocess.run(['node', str(Path(__file__).with_suffix('.cjs')), fixture.server.origin,
                               str(Path(args.saida).resolve()), args.chrome], env=env).returncode
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    raise SystemExit(main())
