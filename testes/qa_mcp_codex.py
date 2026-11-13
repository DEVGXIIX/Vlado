"""Opt-in native CLI regression; disabled synthetic MCPs, no inference or login."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import codex_rpc
from codex_apuracao import TOOLS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', required=True)
    args = parser.parse_args()
    original = codex_rpc.subprocess.Popen
    settings = ('mcp_servers={node_repl={command="fixture-mcp-nao-executar",enabled=false},'
                '"nome.com.ponto"={command="fixture-mcp-nao-executar",enabled=false}}')

    def launch(command, **kwargs):
        return original([*command, '-c', settings], **kwargs)

    with tempfile.TemporaryDirectory(prefix='qa_mcp_codex_') as folder:
        with patch.object(codex_rpc.subprocess, 'Popen', launch):
            rpc = codex_rpc.AppServer(Path(folder), lambda message: None)
        try:
            effective = rpc.call('config/read', {'includeLayers': False})['config']
            config = codex_rpc.mcp_desativados(effective)
            config.update({'permissions.apuracao_acervo.filesystem': {
                ':root': 'deny', ':minimal': 'read', folder: 'read'},
                'permissions.apuracao_acervo.network.enabled': False})
            params = {'cwd': folder, 'permissions': 'apuracao_acervo',
                      'approvalPolicy': 'on-request', 'config': config,
                      'developerInstructions': 'Verificação técnica sintética. Nenhuma pergunta editorial.'}
            started = rpc.call('thread/start', {**params, 'dynamicTools': TOOLS})
            assert started['activePermissionProfile']['id'] == 'apuracao_acervo'
            assert started['sandbox']['type'] == 'readOnly'
            assert started['sandbox']['networkAccess'] is False
            result = {'estado': 'ok', 'versao': rpc.version, 'natureza': 'fixture sintética, executável real',
                      'servidores_fixture': list(config['mcp_servers']),
                      'mcp_desativados': all(s['enabled'] is False for s in config['mcp_servers'].values()),
                      'thread_start': 'ok',
                      'thread_resume': 'não testado no executável: thread sem turno não tem rollout persistido',
                      'turn_start_enviado': False,
                      'inferência_realizada': False}
            output = Path(args.saida)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=True))
        finally:
            rpc.close()


if __name__ == '__main__':
    main()
