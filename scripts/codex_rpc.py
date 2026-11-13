"""Local Codex app-server transport. Never read, copy or log credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading


def seguro(value):
    text = str(value)
    text = re.sub(r'(?i)(bearer\s+|sk-)[\w.\-]+', '[credencial omitida]', text)
    text = re.sub(r'eyJ[\w-]+\.[\w-]+\.[\w-]+', '[token omitido]', text)
    text = re.sub(r'(?i)((?:access_token|refresh_token|id_token|api_key)["\s:=]+)[^\s",}]+', r'\1[omitido]', text)
    return text[:4000]


class ErroCodex(ValueError):
    pass


def selecionar_modelo(rpc, preferido=None):
    """Resolve the runtime catalog; listing alone does not prove inference access."""
    modelos, cursores = [], set()
    cursor = None
    while True:
        params = {'limit': 100, 'includeHidden': False}
        if cursor:
            params['cursor'] = cursor
        result = rpc.call('model/list', params)
        modelos.extend(m for m in result.get('data', [])
                       if isinstance(m, dict) and isinstance(m.get('model'), str)
                       and m['model'].strip() and not m.get('hidden'))
        cursor = result.get('nextCursor')
        if not cursor:
            break
        if cursor in cursores:
            raise ErroCodex('O catálogo de modelos devolveu paginação repetida. Verifique a conexão.')
        cursores.add(cursor)
    if not modelos:
        raise ErroCodex('O Codex não informou modelos disponíveis. Verifique a conexão e a conta ChatGPT.')
    return (next((m for m in modelos if m['model'] == preferido), None)
            or next((m for m in modelos if m.get('isDefault')), None) or modelos[0])


def mcp_desativados(config):
    """Replace the MCP table without inventing quoted names or null TOML values.

    Thread config keys are not shell/TOML expressions. A quoted segment creates
    a literal quoted name, while replacing only `enabled` loses the transport.
    Keep the server descriptors, omit optional nulls, and disable every entry.
    The result stays in backend memory and must never be added to public logs.
    """
    servers = config.get('mcp_servers') or {}
    if not isinstance(servers, dict) or any(not isinstance(value, dict) for value in servers.values()):
        raise ErroCodex('Configuração MCP herdada inválida; conversa não iniciada.')

    def without_nulls(value):
        if isinstance(value, dict):
            return {key: without_nulls(item) for key, item in value.items() if item is not None}
        if isinstance(value, list):
            return [without_nulls(item) for item in value]
        return value

    return {'mcp_servers': {name: {**without_nulls(value), 'enabled': False}
                            for name, value in servers.items()}} if servers else {}


def localizar_codex():
    explicit = os.environ.get('APURACAO_CODEX_BIN')
    candidate = explicit or shutil.which('codex.exe') or shutil.which('codex')
    if not candidate:
        candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/OpenAI/Codex/bin/codex.exe'
    if not Path(candidate).is_file():
        raise ErroCodex('Codex não encontrado. Instale o Codex CLI ou defina APURACAO_CODEX_BIN no backend.')
    if Path(candidate).suffix.lower() in ('.cmd', '.bat', '.ps1'):
        raise ErroCodex('APURACAO_CODEX_BIN deve apontar para o executável nativo do Codex.')
    return str(candidate)


class AppServer:
    def __init__(self, cwd, callback):
        self.callback = callback
        self.pending = {}
        self.lock = threading.RLock()
        self.number = 0
        self.closed = False
        executable = localizar_codex()
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self.version = subprocess.run([executable, '--version'], capture_output=True, text=True,
                                      timeout=10, creationflags=flags).stdout.strip()
        # No API billing fallback; the official runtime owns ChatGPT auth and renewal.
        overrides = {'forced_login_method': 'chatgpt', 'model_provider': 'openai',
                     'web_search': 'disabled', 'project_doc_max_bytes': 0,
                     'features.shell_tool': False, 'features.unified_exec': False,
                     'features.apps': False, 'features.plugins': False,
                     'features.hooks': False, 'features.memories': False,
                     'features.multi_agent': False, 'features.browser_use': False,
                     'features.browser_use_external': False, 'features.computer_use': False,
                     'features.image_generation': False, 'features.code_mode': False,
                     'features.code_mode_host': False, 'features.goals': False,
                     'features.workspace_dependencies': False}
        command = [executable, 'app-server', '--listen', 'stdio://']
        for key, value in overrides.items():
            command += ['-c', f'{key}={json.dumps(value)}']
        env = {k: v for k, v in os.environ.items()
               if k not in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL')}
        self.process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding='utf-8', bufsize=1, creationflags=flags)
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self.call('initialize', {'clientInfo': {'name': 'apuracao_local',
                      'title': 'Mesa de apuração', 'version': '1.3.0'},
                      'capabilities': {'experimentalApi': True}})
            self.send({'method': 'initialized', 'params': {}})
        except Exception:
            self.close()
            raise

    def send(self, message):
        with self.lock:
            if self.closed or self.process.poll() is not None:
                raise ErroCodex('Conexão com o processo Codex encerrada. Tente novamente.')
            try:
                self.process.stdin.write(json.dumps(message, ensure_ascii=False) + '\n')
                self.process.stdin.flush()
            except (OSError, ValueError) as exc:
                raise ErroCodex('Falha de conexão com o Codex local.') from exc

    def call(self, method, params=None, timeout=45):
        with self.lock:
            self.number += 1
            identifier = self.number
            answer = queue.Queue(maxsize=1)
            self.pending[identifier] = answer
        try:
            self.send({'id': identifier, 'method': method, 'params': params or {}})
            try:
                result = answer.get(timeout=timeout)
            except queue.Empty as exc:
                raise ErroCodex('O Codex não respondeu a tempo; confira conexão e autenticação.') from exc
            if 'error' in result:
                raise ErroCodex(seguro(result['error'].get('message', 'Erro do Codex.')))
            return result.get('result', {})
        finally:
            with self.lock:
                self.pending.pop(identifier, None)

    def _read(self):
        try:
            for line in self.process.stdout:
                message = json.loads(line)
                if 'method' not in message:
                    with self.lock:
                        target = self.pending.get(message.get('id'))
                    if target:
                        target.put_nowait(message)
                else:
                    # Callbacks may perform RPCs; never block the protocol reader.
                    self.callback(message)
        except (OSError, ValueError, queue.Full):
            pass
        finally:
            with self.lock:
                self.closed = True
                for answer in self.pending.values():
                    if answer.empty():
                        answer.put_nowait({'error': {'message': 'Conexão com Codex perdida.'}})
            self.callback({'method': 'local/disconnected', 'params': {}})
            if self.process.poll() is None:
                try:
                    self.process.terminate()
                except OSError:
                    pass

    def close(self):
        with self.lock:
            self.closed = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()
