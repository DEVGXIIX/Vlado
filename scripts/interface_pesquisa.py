"""Optional loopback search UI. Uses existing snapshot/index validation and raw logs."""
from __future__ import annotations

import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import hashlib
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
import re
import secrets
import sqlite3
import socket
import sys
import tempfile
import threading
import uuid
from urllib.parse import quote, urlsplit
import webbrowser

from comum import ROOT, dentro, ler_json, sha256
from cadastrar_documentos import cadastrar, inventario, preparar_pdfs
from ambiente import diagnostico
import indice_achados
import revisao_humana
import caderno
import apuracao
import exportar_apuracao
import diligencias
from codex_apuracao import Conversas
from inferencia_api import resumo_inferencia, salvar_inferencia
import acesso
import lixeira
from indice_sqlite import (ID_CASO, ID_RODADA, ID_GERACAO, caminho_rodada,
                           cobertura, ler_passagem, pesquisar)

ASSETS = Path(__file__).resolve().parents[1] / 'interface'
MAX_UPLOAD = 50 * 1024 * 1024
CADERNO_OPERACOES = ('caderno-documentos', 'caderno-listar', 'caderno-detalhe', 'caderno-salvar',
                     'caderno-cruzar', 'caderno-exportar', 'caderno-original')
DILIGENCIAS_OPERACOES = ('diligencias-listar', 'diligencias-criar', 'diligencias-atualizar',
                        'diligencias-responder', 'diligencias-original')
# Provider choice and API key; the key is write-only from the browser's point of view.
IA_OPERACOES = ('ia-config', 'ia-config-salvar')
# Pilot mode: invitations (admin only) and what an invited guest may call.
ACESSO_OPERACOES = ('acesso-listar', 'acesso-criar', 'acesso-revogar')
OPERACOES_CONVIDADO = ('codex-status', 'codex-listar', 'codex-perguntar', 'codex-eventos', 'codex-cancelar',
                       'codex-original', 'sessao-sair')
COOKIE_PILOTO = 'vlado_sessao'


def receber_documentos(root, data):
    files = data.get('arquivos')
    if not isinstance(files, list) or not 1 <= len(files) <= 100:
        raise ValueError('Envie de 1 a 100 arquivos por lote, até 50 MB no total.')
    if type(data.get('novo', False)) is not bool:
        raise ValueError('Indicação de novo caso inválida.')
    with tempfile.TemporaryDirectory(prefix='envio_documental_') as folder:
        sources, total = [], 0
        for number, item in enumerate(files):
            if not isinstance(item, dict):
                raise ValueError('Arquivo enviado inválido; lote não cadastrado.')
            name = item.get('nome')
            if (not isinstance(name, str) or not name or len(name) > 255
                    or PureWindowsPath(name).name != name or PureWindowsPath(name).is_reserved()
                    or name.endswith(('.', ' '))
                    or any(ord(c) < 32 or c in ':\\/<>"|?*' for c in name)):
                raise ValueError('Nome de arquivo inválido; lote não cadastrado.')
            encoded = item.get('base64')
            if not isinstance(encoded, str):
                raise ValueError('Conteúdo de arquivo inválido; lote não cadastrado.')
            content = base64.b64decode(encoded, validate=True)
            total += len(content)
            if total > MAX_UPLOAD:
                raise ValueError('O lote excede 50 MB; nenhum arquivo cadastrado.')
            source = Path(folder) / str(number) / name
            source.parent.mkdir()
            source.write_bytes(content)
            sources.append(source)
        case = data.get('caso')
        if data.get('novo') and not case:
            case = 'apuracao_' + uuid.uuid4().hex
        return cadastrar(root, case, sources, titulo=data.get('titulo'),
                         natureza=data.get('natureza', 'nao_informada'), novo=data.get('novo', False))


def catalogo(root):
    """Read catalog metadata and directory names only; do not read inactive documents."""
    path = root / 'casos/catalogo.json'
    cases = ler_json(path)['casos'] if path.is_file() else []
    result = []
    removed = lixeira.ativos(root)
    for case in cases:
        identifier = case['id']
        if not re.fullmatch(ID_CASO, identifier):
            continue
        if lixeira.excluido(root, identifier, itens=removed):
            continue
        rounds = []
        folder = dentro(root, f'execucoes/{identifier}')
        try:
            runs = sorted(folder.iterdir()) if folder.is_dir() else []
        except PermissionError:
            result.append({'id': identifier, 'titulo': case.get('titulo', identifier),
                           'rodadas': [], 'aviso': 'Sem permissão para listar rodadas deste caso.'})
            continue
        for run in runs:
            if not re.fullmatch(ID_RODADA, run.name) or not run.is_dir():
                continue
            if lixeira.excluido(root, identifier, rodada=run.name, itens=removed):
                continue
            run = dentro(root, f'execucoes/{identifier}/{run.name}')
            index = dentro(run, 'indice')
            try:
                generations = [item.name for item in sorted(index.iterdir())
                               if re.fullmatch(ID_GERACAO, item.name)
                               and dentro(index, item.name).is_dir()
                               and dentro(index, f'{item.name}/manifesto.json').is_file()
                               and dentro(index, f'{item.name}/apuracao.sqlite').is_file()] if index.is_dir() else []
                rounds.append({'id': run.name, 'geracoes': generations})
            except PermissionError:
                rounds.append({'id': run.name, 'geracoes': [],
                               'aviso': 'Sem permissão para listar índices desta rodada.'})
        result.append({'id': identifier, 'titulo': case.get('titulo', identifier), 'rodadas': rounds})
    return {'casos': result}


def executar(root, operation, data):
    if operation == 'analises':
        case = data.get('caso')
        if not isinstance(case, str) or not re.fullmatch(ID_CASO, case):
            raise ValueError('Selecione uma apuração válida.')
        selected = next((c for c in catalogo(root)['casos'] if c['id'] == case), None)
        if selected is None:
            raise ValueError('Apuração indisponível.')
        result = []
        for item in selected['rodadas']:
            run = caminho_rodada(root, case, item['id'])
            try:
                record = ler_json(dentro(run, 'registro.json'))
                if record['caso_id'] != case or record['rodada'] != item['id']:
                    raise ValueError('Identidade da análise divergente.')
                question = dentro(run, '00_pergunta_original.md')
                frozen = ler_json(dentro(run, 'snapshot.json'))
                expected = next(x['sha256'] for x in frozen if x['arquivo'] == '00_pergunta_original.md')
                if sha256(question) != expected:
                    raise ValueError('Pergunta preservada divergente.')
                result.append({**item, 'pergunta': question.read_text(encoding='utf-8'),
                    'data': record.get('criada_em_utc'), 'documentos': record.get('corpus_id')})
            except (ValueError, OSError, KeyError, StopIteration, TypeError) as exc:
                result.append({**item, 'aviso': str(exc)})
        return {'caso': case, 'analises': result}
    if operation.startswith('apuracao-'):
        if operation == 'apuracao-listar':
            return apuracao.listar(root, data.get('caso'))
        return apuracao.alterar(root, operation, data)
    if operation.startswith('diligencias-'):
        if operation == 'diligencias-listar':
            return diligencias.listar(root, data.get('caso'), estado=data.get('estado', ''),
                responsavel=data.get('responsavel', ''), texto=data.get('texto', ''))
        if operation in ('diligencias-criar', 'diligencias-atualizar', 'diligencias-responder'):
            return diligencias.salvar(root, data, operation.split('-')[1])
        raise ValueError('Operação de diligência desconhecida.')
    if operation.startswith('caderno-'):
        case = data.get('caso')
        if operation == 'caderno-documentos':
            return caderno.documentos(root, case, data.get('rodada'))
        if operation == 'caderno-listar':
            return caderno.listar(root, case, texto=data.get('texto', ''), limite=data.get('limite', 20), deslocamento=data.get('deslocamento', 0))
        if operation == 'caderno-detalhe':
            return caderno.detalhe(root, case, data.get('registro_id'), data.get('sha256'))
        if operation == 'caderno-salvar':
            return caderno.salvar(root, data)
        if operation == 'caderno-cruzar':
            return caderno.cruzar(root, data)
        if operation == 'caderno-exportar':
            return caderno.selecionar(root, case, data.get('selecoes'))
        raise ValueError('Operação do caderno desconhecida.')
    if operation == 'cadastrar':
        return receber_documentos(root, data)
    if operation == 'inventario':
        return inventario(root, data.get('caso'))
    if operation == 'preparar-pdfs':
        if not diagnostico()['extracao_pdf']['disponivel']:
            raise ValueError('O extrator de PDF não está disponível nesta instância. Encerre a Mesa e abra pelo iniciador atualizado.')
        return preparar_pdfs(root, data.get('caso'))
    case, run = data.get('caso'), data.get('rodada')
    lixeira.conferir_disponivel(root, case, rodada=run)
    if operation.startswith('achados-'):
        # Explicit identities; human annotations never alter canonical AI records.
        if operation == 'achados-catalogo':
            return indice_achados.catalogo(root, case, run)
        revision, gen = data.get('revisao'), data.get('geracao_achados')
        if operation == 'achados-revisao-salvar':
            return revisao_humana.salvar(root, case, run, revision,
                achado_id=data.get('achado_id'), achado_versao=data.get('achado_versao'),
                registros_sha256=data.get('registros_sha256'), estado=data.get('estado'),
                observacao=data.get('observacao', ''), anterior=data.get('anterior'))
        if operation == 'achados-briefing':
            digest = data.get('artefato_sha256')
            if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                raise ValueError('Identidade de briefing inválida.')
            return indice_achados.artefato(root, case, run, revision, digest)
        if operation in ('achados-evidencia', 'achados-original'):
            evidence_id = data.get('evidencia_id')
            if not isinstance(evidence_id, str) or not re.fullmatch(r'E[0-9]{3,}', evidence_id):
                raise ValueError('ID de evidência inválido.')
            return indice_achados.evidencia(root, case, run, revision, evidence_id)
        if operation == 'achados-detalhe':
            claim_id = data.get('achado_id')
            if not isinstance(claim_id, str) or not re.fullmatch(r'A[0-9]{3,}', claim_id):
                raise ValueError('ID de achado inválido.')
            return revisao_humana.detalhe(root, case, run, revision, gen, claim_id)
        if operation in ('achados-buscar', 'achados-exportar'):
            return revisao_humana.consultar(root, case, run, revision, gen,
                       filtros=data.get('filtros'), limite=data.get('limite', 10),
                       deslocamento=data.get('deslocamento', 0), completa=operation == 'achados-exportar')
        raise ValueError('Operação de achados desconhecida.')
    generation = data.get('geracao', 'v1')
    if not all(isinstance(value, str) for value in (case, run, generation)):
        raise ValueError('Selecione caso, rodada e geração.')
    if operation == 'cobertura':
        return cobertura(root, case, run, generation)
    if operation in ('ler', 'original'):
        reference = data.get('referencia')
        if not isinstance(reference, str) or not re.fullmatch(r'[a-f0-9]{64}', reference):
            raise ValueError('Referência de passagem inválida.')
        return ler_passagem(root, case, run, reference, geracao=generation)
    if operation == 'buscar':
        documents = data.get('documentos')
        if documents is not None and (not isinstance(documents, list)
                                     or not all(isinstance(x, str) for x in documents)):
            raise ValueError('Filtro de documentos inválido.')
        for key in ('limite', 'deslocamento', 'pagina'):
            value = data.get(key)
            if value is not None and type(value) is not int:
                raise ValueError('Página, limite e deslocamento devem ser números inteiros.')
        return pesquisar(root, case, run, data.get('consulta'), modo=data.get('modo', 'comum'),
                         documentos=documents, pagina=data.get('pagina'),
                         limite=data.get('limite', 10), deslocamento=data.get('deslocamento', 0),
                         geracao=generation)
    raise ValueError('Operação desconhecida.')


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        # SO_REUSEADDR permits multiple independent Windows servers on one port.
        # Each browser request could then hit a different backend version.
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address, root=ROOT, modo='local', origem=None):
        if modo not in ('local', 'piloto'):
            raise ValueError('Modo inválido: use local ou piloto.')
        if modo == 'piloto':
            partes = urlsplit(origem or '')
            if partes.scheme != 'https' or not partes.netloc or partes.path not in ('', '/') or partes.query:
                raise ValueError('No modo piloto informe --origem com o endereço público HTTPS, ex.: https://vlado.example.org')
        self.modo = modo
        self.origem_publica = (origem or '').rstrip('/')
        self.root = Path(root).resolve()
        self.token = secrets.token_urlsafe(32)
        self.ambiente = diagnostico()
        self.cadastro_lock = threading.Lock()
        self.conversas = Conversas(self.root)
        super().__init__(address, Handler)

    def server_close(self):
        self.conversas.close()
        super().server_close()

    @property
    def origin(self):
        return self.origem_publica if self.modo == 'piloto' else f'http://127.0.0.1:{self.server_port}'

    @property
    def host_permitido(self):
        return urlsplit(self.origem_publica).netloc if self.modo == 'piloto' else f'127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    timeout = 60  # seconds per socket operation; long polls answer within 20 s
    def _send(self, status, content, content_type='application/json; charset=utf-8', extra=None, cache='no-store'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', cache)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self' blob:; img-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header('Referrer-Policy', 'no-referrer')
        if self.server.modo == 'piloto':
            self.send_header('Strict-Transport-Security', 'max-age=31536000')
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        try:
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Reloading/closing a tab may abandon an in-flight poll. Do not try
            # to send a second error response over the already closed socket.
            self.close_connection = True

    def _json(self, status, value):
        self._send(status, json.dumps(value, ensure_ascii=False).encode('utf-8'))

    def _allowed(self):
        if urlsplit(self.path).path == '/saude':
            return True  # container healthcheck reaches the server by its internal address
        if self.headers.get('Host') != self.server.host_permitido:
            self._json(403, {'erro': 'Endereço não autorizado.'})
            return False
        return True

    def _sessao_piloto(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:  # noqa: BLE001 - malformed cookie header means no session
            return None, None
        morsel = cookie.get(COOKIE_PILOTO)
        sid = morsel.value if morsel else None
        if not sid:
            return None, None
        try:
            return acesso.sessao(self.server.root, sid), sid
        except (ValueError, OSError):
            self.acesso_indisponivel = True  # answered with 503, never with a dropped connection
            return None, sid

    def _principal(self):
        """Who is calling: in local mode the single operator (admin); in pilot mode the invitation session."""
        if self.server.modo == 'local':
            return {'papel': 'admin', 'convite': None, 'casos': None, 'csrf': self.server.token}
        return self._sessao_piloto()[0]

    def _proibido(self, mensagem='Operação não permitida para este acesso.'):
        self._json(403, {'estado': 'proibido', 'erro': mensagem})

    def _sem_principal(self, api=False):
        if getattr(self, 'acesso_indisponivel', False):
            self._json(503, {'estado': 'indisponivel', 'erro': 'Registro de acesso indisponível. Avise a administração.'})
        elif api:
            self._json(401, {'estado': 'sem_sessao', 'erro': 'Sessão expirada ou convite revogado. Abra novamente o link do convite.'})
        else:
            self._sem_convite()

    def _sem_convite(self):
        texto = ('Acesso somente por convite. Abra o link que você recebeu. / '
                 'Access by invitation only. Open the link you received.')
        self._send(401, f'<!doctype html><meta charset="utf-8"><title>Vlado</title><p>{texto}</p>'.encode('utf-8'),
                   'text/html; charset=utf-8')

    def _aceitar_convite(self, token):
        try:
            sid, _ = acesso.aceitar(self.server.root, token)
        except ValueError as exc:
            self._send(403, f'<!doctype html><meta charset="utf-8"><title>Vlado</title><p>{exc}</p>'.encode('utf-8'),
                       'text/html; charset=utf-8')
            return
        cookie = (f'{COOKIE_PILOTO}={sid}; HttpOnly; Secure; SameSite=Strict; Path=/; '
                  f'Max-Age={acesso.SESSAO_HORAS * 3600}')
        # Guests land on the ask area; with a single released case it is already selected.
        try:
            casos = (acesso.sessao(self.server.root, sid) or {}).get('casos') or []
        except (ValueError, OSError):
            casos = []
        destino = '/?area=codex' + (f'&caso={quote(casos[0], safe="")}' if len(casos) == 1 else '')
        self._send(303, b'', 'text/plain; charset=utf-8', {'Location': destino, 'Set-Cookie': cookie})

    def do_GET(self):
        if not self._allowed():
            return
        path = urlsplit(self.path).path
        if path == '/saude':
            self._json(200, {'ok': True})
            return
        if self.server.modo == 'piloto':
            if path.startswith('/convite/'):
                self._aceitar_convite(path.removeprefix('/convite/'))
                return
            if path in ('/', '/api/catalogo') and self._principal() is None:
                self._sem_principal(api=path != '/')
                return
        if path == '/api/integracao':
            self._json(200, {'codex': True, 'protocolo_interface': 1, 'gerenciamento': True,
                             'apresentacao_editorial': True, 'preparacao_pdfs': True,
                             'revisao_humana': True, 'continuar_observacoes': True, 'continuar_documentos': True, 'caderno_humano': True, 'diligencias': True,
                             'extracao_pdf': self.server.ambiente['extracao_pdf']})
            return
        if path == '/api/catalogo':
            try:
                dados, principal = catalogo(self.server.root), self._principal()
                if principal['casos'] is not None:
                    dados = {'casos': [c for c in dados['casos'] if c['id'] in principal['casos']]}
                self._json(200, dados)
            except (ValueError, OSError, KeyError) as exc:
                self._json(400, {'erro': str(exc)})
            return
        assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/codex.js': ('codex.js', 'text/javascript; charset=utf-8'),
                  '/i18n.js': ('i18n.js', 'text/javascript; charset=utf-8'),
                  '/i18n_en.js': ('i18n_en.js', 'text/javascript; charset=utf-8'),
                  '/configuracao_ia.js': ('configuracao_ia.js', 'text/javascript; charset=utf-8'),
                  '/piloto.js': ('piloto.js', 'text/javascript; charset=utf-8'),
                  '/gerenciar.js': ('gerenciar.js', 'text/javascript; charset=utf-8'),
                  '/leitura.js': ('leitura.js', 'text/javascript; charset=utf-8'),
                  '/experiencia.js': ('experiencia.js', 'text/javascript; charset=utf-8'),
                  '/desktop.js': ('desktop.js', 'text/javascript; charset=utf-8'),
                  '/revisao.js': ('revisao.js', 'text/javascript; charset=utf-8'),
                  '/diligencias.js': ('diligencias.js', 'text/javascript; charset=utf-8'),
                  '/observacoes.js': ('observacoes.js', 'text/javascript; charset=utf-8'),
                  '/continuidade.js': ('continuidade.js', 'text/javascript; charset=utf-8'),
                  '/caderno.js': ('caderno.js', 'text/javascript; charset=utf-8'),
                  '/apuracao.js': ('apuracao.js', 'text/javascript; charset=utf-8'),
                  '/editor_notas.js': ('editor_notas.js', 'text/javascript; charset=utf-8'),
                  '/vendor/vditor/dist/index.min.js': ('vendor/vditor/dist/index.min.js', 'text/javascript; charset=utf-8'),
                  '/vendor/vditor/dist/index.css': ('vendor/vditor/dist/index.css', 'text/css; charset=utf-8'),
                  '/vendor/vditor/dist/js/lute/lute.min.js': ('vendor/vditor/dist/js/lute/lute.min.js', 'text/javascript; charset=utf-8'),
                  '/vendor/vditor/dist/js/i18n/pt_BR.js': ('vendor/vditor/dist/js/i18n/pt_BR.js', 'text/javascript; charset=utf-8'),
                  '/vendor/vditor/dist/js/icons/ant.js': ('vendor/vditor/dist/js/icons/ant.js', 'text/javascript; charset=utf-8'),
                  '/vendor/vditor/dist/css/content-theme/light.css': ('vendor/vditor/dist/css/content-theme/light.css', 'text/css; charset=utf-8'),
                  '/fonts/SourceSerif4-Roman.ttf': ('fonts/SourceSerif4-Roman.ttf', 'font/ttf'),
                  '/fonts/SourceSans3-Upright.otf': ('fonts/SourceSans3-Upright.otf', 'font/otf'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path not in assets:
            self._json(404, {'erro': 'Página não encontrada.'})
            return
        name, content_type = assets[path]
        content = (ASSETS / name).read_bytes()
        if name == 'index.html':
            principal = self._principal()
            piloto = self.server.modo == 'piloto'
            content = (content.replace(b'__SESSION_TOKEN__', principal['csrf'].encode('ascii'))
                       .replace(b'__IDIOMA_PADRAO__', b'en' if piloto else b'pt')
                       .replace(b'__PAPEL__', principal['papel'].encode('ascii'))
                       .replace(b'__MODO__', self.server.modo.encode('ascii')))
            extra = {} if piloto else {'Set-Cookie': f'apuracao_session={self.server.token}; HttpOnly; SameSite=Strict; Path=/'}
            self._send(200, content, content_type, extra)
        else:
            # Static files revalidate on every load (no stale code after an update) but skip the
            # download when unchanged; index.html stays no-store because it carries session tokens.
            etag = '"' + hashlib.sha256(content).hexdigest()[:32] + '"'
            if self.headers.get('If-None-Match') == etag:
                self._send(304, b'', content_type, {'ETag': etag}, cache='no-cache')
            else:
                self._send(200, content, content_type, {'ETag': etag}, cache='no-cache')

    def do_POST(self):
        if self.server.modo == 'piloto':
            # Never read (up to 72 MB of) a body for anonymous or foreign-host requests.
            if not self._allowed():
                self.close_connection = True
                return
            if self._principal() is None:
                self.close_connection = True
                self._sem_principal(api=True)
                return
        # Consume bounded bodies even for rejected requests, avoiding TCP resets on Windows.
        try:
            length = int(self.headers.get('Content-Length', '0'))
            operation = urlsplit(self.path).path.removeprefix('/api/')
            maximum = (72 * 1024 * 1024 if operation in ('cadastrar', 'codex-documentos-cadastrar')
                       else 2 * 1024 * 1024 if operation in apuracao.OPERACOES
                       else 128 * 1024 if operation in ('caderno-salvar', 'diligencias-criar', 'diligencias-atualizar', 'diligencias-responder') else 32768)
            if not 0 < length <= maximum:
                raise ValueError('Requisição vazia ou muito grande.')
            body = self.rfile.read(length)
        except ValueError as exc:
            self._json(400, {'erro': str(exc)})
            return
        if not self._allowed():
            return
        principal = self._principal()
        if principal is None:
            self._sem_principal(api=True)
            return
        # Pilot mode requires an explicit Origin; local mode keeps accepting same-origin requests without it.
        origem = self.headers.get('Origin', None if self.server.modo == 'piloto' else self.server.origin)
        if (origem != self.server.origin
                or not secrets.compare_digest(self.headers.get('X-Session-Token', '').encode('utf-8'), principal['csrf'].encode('ascii'))
                or self.headers.get_content_type() != 'application/json'):
            self._json(403, {'erro': 'Origem ou sessão não autorizada. Recarregue a página.'})
            return
        operation = urlsplit(self.path).path.removeprefix('/api/')
        # Operation names keep the historical "codex-" prefix; inference now goes through the API adapter.
        codex_operations = ('codex-status', 'codex-listar',
                            'codex-perguntar', 'codex-eventos', 'codex-cancelar', 'codex-original',
                            'codex-desligar', 'codex-observacoes', 'codex-corpus-previa', 'codex-documentos-cadastrar', 'codex-caderno-previa', 'codex-diligencias-previa')
        if operation not in (*codex_operations, *apuracao.OPERACOES, *CADERNO_OPERACOES, *DILIGENCIAS_OPERACOES, 'analises', 'buscar', 'ler', 'cobertura', 'original', 'cadastrar', 'inventario',
                             'ambiente', 'preparar-pdfs',
                             'gerenciar-listar', 'excluir', 'restaurar', 'lixeira-alcance', 'lixeira-apagar', *IA_OPERACOES, *ACESSO_OPERACOES, 'sessao-sair',
                             'achados-revisao-salvar',
                             'achados-catalogo', 'achados-buscar', 'achados-detalhe',
                             'achados-evidencia', 'achados-original', 'achados-exportar', 'achados-briefing'):
            self._json(404, {'erro': 'Operação não encontrada.'})
            return
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError('Requisição deve ser um objeto JSON.')
            negado = self._negado(operation, data, principal)
            if negado:
                self._proibido(negado)
                return
            dono = principal['convite'] if principal['papel'] != 'admin' else None
            if operation == 'sessao-sair':
                acesso.encerrar(self.server.root, self._sessao_piloto()[1])
                self._send(200, b'{"estado": "encerrada"}', extra={
                    'Set-Cookie': f'{COOKIE_PILOTO}=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0'})
                return
            if operation in ACESSO_OPERACOES:
                self._json(200, self._acesso(operation, data))
                return
            consulta_contada = False
            if operation == 'codex-perguntar' and dono is not None:
                acesso.registrar_consulta(self.server.root, dono)
                consulta_contada = True
            if operation == 'ambiente':
                result = self.server.ambiente
            elif operation == 'ia-config':
                result = resumo_inferencia(self.server.root)
            elif operation == 'ia-config-salvar':
                result = salvar_inferencia(self.server.root, data)
            elif operation == 'apuracao-exportar':
                with self.server.cadastro_lock:
                    state = apuracao.listar(self.server.root, data.get('caso'))
                content, mime = exportar_apuracao.exportar(state, data.get('formato'))
                self._send(200, content, mime, {'Content-Disposition': f'attachment; filename="caderno.{data["formato"]}"'})
                return
            elif operation == 'apuracao-original':
                with self.server.cadastro_lock:
                    path = apuracao.original(self.server.root, data)
                    self._send(200, path.read_bytes(), 'application/octet-stream',
                               {'Content-Disposition': f'attachment; filename="original{path.suffix}"'})
                return
            elif operation == 'diligencias-original':
                with self.server.cadastro_lock:
                    path = diligencias.original_resposta(self.server.root, data)
                    self._send(200, path.read_bytes(), 'application/octet-stream',
                               {'Content-Disposition': f'attachment; filename="original{path.suffix}"'})
                return
            elif operation == 'caderno-original':
                with self.server.cadastro_lock:
                    path = (caderno.original_registro(self.server.root, data) if data.get('registro_id')
                            else caderno.original_documento(self.server.root, data))
                    self._send(200, path.read_bytes(), 'application/octet-stream',
                               {'Content-Disposition': f'attachment; filename="original{path.suffix}"'})
                return
            elif operation == 'lixeira-alcance':
                result = lixeira.alcance(self.server.root, data.get('item'))
            elif operation == 'lixeira-apagar':
                with self.server.cadastro_lock:
                    alcance = lixeira.alcance(self.server.root, data.get('item'))
                    nome = data.get('nome')
                    if (not isinstance(nome, str)
                            or nome.strip().casefold() != str(alcance['nome_para_confirmar']).strip().casefold()):
                        raise ValueError('Digite o nome do item exatamente como mostrado para confirmar.')
                    result = lixeira.apagar_definitivamente(
                        self.server.root, data.get('item'), data.get('confirmacao'),
                        quem=principal.get('nome') or principal.get('convite') or 'operador local',
                        gerenciador=self.server.conversas)
            elif operation in ('gerenciar-listar', 'excluir', 'restaurar'):
                with self.server.cadastro_lock:
                    manager = self.server.conversas
                    if operation == 'gerenciar-listar':
                        with manager.lock:
                            visible = catalogo(self.server.root)
                            selected = data.get('caso')
                            result = {**visible, 'lixeira': lixeira.ativos(self.server.root),
                                      'conversas': manager.listar(selected)['conversas']
                                      if selected in {c['id'] for c in visible['casos']} else []}
                    else:
                        result = manager.gerenciar(operation, data)
            elif operation in codex_operations:
                manager = self.server.conversas
                if operation == 'codex-desligar':
                    self._json(200, {'estado': 'encerrando'})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if operation == 'codex-original':
                    path = manager.fonte(data.get('conversa'), data.get('referencia'), dono=dono)
                    self._send(200, path.read_bytes(), 'application/octet-stream',
                               {'Content-Disposition': f'attachment; filename="original{path.suffix}"'})
                    return
                if operation == 'codex-status':
                    result = manager.status()
                elif operation == 'codex-listar':
                    result = manager.listar(data.get('caso'), dono=dono)
                elif operation == 'codex-perguntar':
                    try:
                        result = manager.perguntar(data, dono=dono)
                    except Exception:
                        if consulta_contada:
                            acesso.devolver_consulta(self.server.root, dono)
                        raise
                elif operation == 'codex-observacoes':
                    result = manager.observacoes(data)
                elif operation == 'codex-corpus-previa':
                    result = manager.preparar_corpus(data)
                elif operation == 'codex-caderno-previa':
                    result = manager.caderno_previa(data)
                elif operation == 'codex-diligencias-previa':
                    result = manager.caderno_previa(data, diligencias)
                elif operation == 'codex-documentos-cadastrar':
                    with self.server.cadastro_lock, manager.lock:
                        manager.conferir_para_documentos(data.get('caso'), data.get('conversa'))
                        result = receber_documentos(self.server.root, {'caso': data.get('caso'),
                            'arquivos': data.get('arquivos'), 'natureza': data.get('natureza', 'nao_informada')})
                elif operation == 'codex-eventos':
                    result = manager.eventos(data.get('conversa'), data.get('cursor', 0), data.get('espera', 0), dono=dono)
                elif operation == 'codex-cancelar':
                    result = manager.cancelar(data.get('conversa'), dono=dono)
            else:
                with self.server.cadastro_lock:
                    result = executar(self.server.root, operation, data)
            if operation in ('original', 'achados-original'):
                # Resolve only the original returned by a validated passage, never a client path.
                run = caminho_rodada(self.server.root, data['caso'], data['rodada'])
                path = dentro(run, result['evidencia' if operation == 'achados-original' else 'passagem']['original'])
                self._send(200, path.read_bytes(), 'application/octet-stream',
                           {'Content-Disposition': 'attachment; filename="original.bin"'})
            else:
                self._json(400 if result.get('estado') == 'erro_consulta' else 200, result)
        except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
            convidado = principal['papel'] != 'admin'
            mensagem = ('Falha ao ler arquivos do servidor.' if convidado and isinstance(exc, OSError) else str(exc))
            self._json(400, {'estado': 'erro', 'erro': mensagem})

    def _negado(self, operation, data, principal):
        """Authorization by role. Returns the refusal message, or None when allowed."""
        if self.server.modo == 'piloto' and operation == 'codex-desligar':
            return 'O serviço hospedado não pode ser encerrado pela interface.'
        if operation in ACESSO_OPERACOES and self.server.modo != 'piloto':
            return 'Convites só existem no modo piloto.'
        if principal['papel'] == 'admin':
            return None
        if operation not in OPERACOES_CONVIDADO:
            return 'Operação não permitida para convidados.'
        if operation in ('codex-listar', 'codex-perguntar') and data.get('caso') not in (principal['casos'] or []):
            return 'Apuração não liberada para este convite.'
        if operation == 'codex-perguntar' and set(data) - {'caso', 'pergunta', 'conversa'}:
            return 'Convidados enviam somente a pergunta e a conversa.'
        return None

    def _acesso(self, operation, data):
        root = self.server.root
        if operation == 'acesso-listar':
            return {'convites': acesso.listar(root)}
        if operation == 'acesso-revogar':
            return {'convite': acesso.revogar(root, data.get('id'))}
        casos = data.get('casos')
        disponiveis = {c['id'] for c in catalogo(root)['casos']}
        if not isinstance(casos, list) or not set(casos) <= disponiveis:
            raise ValueError('Escolha apurações existentes para o convite.')
        registro, token = acesso.criar_convite(root, data.get('nome'), casos=casos,
                                               cota_diaria=data.get('cota_diaria', 20), dias=data.get('dias', 14))
        return {'convite': registro, 'link': f'{self.server.origin}/convite/{token}'}

    def log_message(self, format, *args):
        # Do not print queries, source content or token to the terminal.
        return


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porta', type=int, default=8765)
    parser.add_argument('--sem-abrir', action='store_true')
    parser.add_argument('--modo', choices=('local', 'piloto'), default='local',
                        help='piloto: acesso por convite atrás de um proxy HTTPS (ver docs/IMPLANTACAO_PILOTO.md)')
    parser.add_argument('--host', default='127.0.0.1', help='Endereço de escuta; no contêiner use 0.0.0.0')
    parser.add_argument('--origem', help='Endereço público HTTPS do piloto, ex.: https://vlado.example.org')
    args = parser.parse_args()
    if args.modo == 'local' and args.host != '127.0.0.1':
        raise SystemExit('No modo local o servidor escuta somente em 127.0.0.1.')
    with Servidor((args.host, args.porta), modo=args.modo, origem=args.origem) as server:
        print(f'Mesa de apuração ({args.modo}): {server.origin}', flush=True)
        print('Encerre com Ctrl+C.', flush=True)
        if args.modo == 'local' and not args.sem_abrir:
            webbrowser.open(server.origin)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    try:
        main()
    except OSError as exc:
        if os.name == 'nt' and os.environ.get('APURACAO_OCULTO') == '1':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f'Não foi possível iniciar a Mesa de apuração.\n{exc}\nSe a porta 8765 estiver ocupada, encerre o servidor anterior.', 'Mesa de apuração', 16)
        else:
            raise
