"""Pilot access control: admin bootstrap, guest invitations and server-side sessions.

Tokens and session ids are random (secrets.token_urlsafe) and only their SHA-256
is stored. The store lives in acesso/acesso.json (gitignored) or in the path
given by VLADO_ACESSO (e.g. a Docker volume). Revoking an invitation invalidates
its sessions on the next request.

CLI (run on the server; prints a one-time link):
  python scripts/acesso.py criar-admin --nome "Grupo VLADO" --origem https://vlado.example.org
  python scripts/acesso.py criar-convite --nome "Convidada" --casos caso_a,caso_b --cota 20 --dias 14 --origem ...
  python scripts/acesso.py listar
  python scripts/acesso.py revogar ID
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadastrar_documentos import _atomico  # noqa: E402

PAPEIS = ('admin', 'convidado')
ID_CASO = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
SESSAO_HORAS = 12
_TRAVA = threading.RLock()


def agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(momento: datetime) -> str:
    return momento.strftime('%Y-%m-%dT%H:%M:%SZ')


def _data(texto: str) -> datetime:
    return datetime.strptime(texto, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode('utf-8')).hexdigest()


def caminho(root: Path) -> Path:
    destino = os.environ.get('VLADO_ACESSO', '').strip()
    return Path(destino) if destino else Path(root) / 'acesso' / 'acesso.json'


def _ler(root: Path) -> dict:
    arquivo = caminho(root)
    if not arquivo.is_file():
        return {'versao': 1, 'convites': {}, 'sessoes': {}, 'uso': {}}
    try:
        dados = json.loads(arquivo.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('Registro de acesso ilegível; restaure o backup de acesso/.') from exc
    for chave in ('convites', 'sessoes', 'uso'):
        dados.setdefault(chave, {})
    return dados


def _gravar(root: Path, dados: dict) -> None:
    arquivo = caminho(root)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    _atomico(arquivo, (json.dumps(dados, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    try:
        os.chmod(arquivo, 0o600)
    except OSError:
        pass


def _publico(cid: str, convite: dict, momento: datetime) -> dict:
    situacao = ('revogado' if convite.get('revogado')
                else 'expirado' if convite.get('expira_em') and _data(convite['expira_em']) <= momento else 'ativo')
    return {'id': cid, 'nome': convite['nome'], 'papel': convite['papel'], 'casos': convite.get('casos'),
            'cota_diaria': convite.get('cota_diaria'), 'expira_em': convite.get('expira_em'),
            'criado_em': convite['criado_em'], 'situacao': situacao}


def _valido(convite: dict | None, momento: datetime) -> bool:
    return bool(convite) and not convite.get('revogado') and not (
        convite.get('expira_em') and _data(convite['expira_em']) <= momento)


def criar_convite(root: Path, nome, papel='convidado', casos=(), cota_diaria=20, dias=14):
    """Return (public record, token). The token is shown once and never stored."""
    if not isinstance(nome, str) or not nome.strip() or len(nome) > 120:
        raise ValueError('Informe o nome de quem recebe o convite (até 120 caracteres).')
    if papel not in PAPEIS:
        raise ValueError('Papel de acesso inválido.')
    if papel == 'convidado':
        if not isinstance(casos, (list, tuple)) or not casos or len(casos) > 50 or not all(
                isinstance(c, str) and ID_CASO.fullmatch(c) for c in casos):
            raise ValueError('Escolha ao menos uma apuração válida para o convidado.')
        if type(cota_diaria) is not int or not 1 <= cota_diaria <= 500:
            raise ValueError('A cota diária deve ser um número entre 1 e 500.')
    if type(dias) is not int or not 1 <= dias <= 365:
        raise ValueError('A validade deve ficar entre 1 e 365 dias.')
    momento = agora()
    token, cid = secrets.token_urlsafe(32), secrets.token_hex(8)
    convite = {'nome': nome.strip(), 'papel': papel,
               'casos': sorted(set(casos)) if papel == 'convidado' else None,
               'cota_diaria': cota_diaria if papel == 'convidado' else None,
               'expira_em': _iso(momento + timedelta(days=dias)), 'criado_em': _iso(momento),
               'revogado': False, 'token_sha256': _hash(token)}
    with _TRAVA:
        dados = _ler(root)
        dados['convites'][cid] = convite
        _gravar(root, dados)
    return _publico(cid, convite, momento), token


def listar(root: Path) -> list[dict]:
    momento = agora()
    with _TRAVA:
        return [_publico(cid, c, momento) for cid, c in sorted(_ler(root)['convites'].items(),
                                                              key=lambda item: item[1]['criado_em'])]


def revogar(root: Path, cid) -> dict:
    with _TRAVA:
        dados = _ler(root)
        convite = dados['convites'].get(cid) if isinstance(cid, str) else None
        if not convite:
            raise ValueError('Convite não encontrado.')
        convite['revogado'] = True
        dados['sessoes'] = {k: s for k, s in dados['sessoes'].items() if s['convite'] != cid}
        _gravar(root, dados)
        return _publico(cid, convite, agora())


def aceitar(root: Path, token) -> tuple[str, str]:
    """Exchange an invitation token for a new session; returns (session id, csrf token)."""
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        raise ValueError('Convite inválido ou revogado.')
    momento = agora()
    with _TRAVA:
        dados = _ler(root)
        digest = _hash(token)
        cid = next((k for k, c in dados['convites'].items()
                    if secrets.compare_digest(c['token_sha256'], digest)), None)
        convite = dados['convites'].get(cid)
        if not _valido(convite, momento):
            raise ValueError('Convite inválido, expirado ou revogado.')
        sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expira = min(momento + timedelta(hours=SESSAO_HORAS), _data(convite['expira_em']))
        # Drop expired sessions while writing; the store stays small.
        dados['sessoes'] = {k: s for k, s in dados['sessoes'].items() if _data(s['expira_em']) > momento}
        dados['sessoes'][_hash(sid)] = {'convite': cid, 'csrf': csrf, 'criada_em': _iso(momento),
                                        'expira_em': _iso(expira)}
        _gravar(root, dados)
    return sid, csrf


def sessao(root: Path, sid) -> dict | None:
    if not isinstance(sid, str) or not 20 <= len(sid) <= 100:
        return None
    momento = agora()
    with _TRAVA:
        dados = _ler(root)
        registro = dados['sessoes'].get(_hash(sid))
        if not registro or _data(registro['expira_em']) <= momento:
            return None
        convite = dados['convites'].get(registro['convite'])
        if not _valido(convite, momento):
            return None
        return {'convite': registro['convite'], 'nome': convite['nome'], 'papel': convite['papel'],
                'casos': convite.get('casos'), 'cota_diaria': convite.get('cota_diaria'), 'csrf': registro['csrf'],
                'expira_em': registro['expira_em']}


def encerrar(root: Path, sid) -> None:
    if not isinstance(sid, str):
        return
    with _TRAVA:
        dados = _ler(root)
        if dados['sessoes'].pop(_hash(sid), None) is not None:
            _gravar(root, dados)


def registrar_consulta(root: Path, cid: str) -> int:
    """Count one question for today (UTC). Guests over their daily quota are refused."""
    dia = agora().strftime('%Y-%m-%d')
    with _TRAVA:
        dados = _ler(root)
        convite = dados['convites'].get(cid)
        if not _valido(convite, agora()):
            raise ValueError('Convite inválido, expirado ou revogado.')
        uso = dados['uso'].setdefault(cid, {})
        feitas = uso.get(dia, 0)
        if convite.get('cota_diaria') is not None and feitas >= convite['cota_diaria']:
            raise ValueError(f'Limite diário de {convite["cota_diaria"]} pergunta(s) atingido. Tente novamente amanhã.')
        dados['uso'][cid] = {dia: feitas + 1}  # keep only today
        _gravar(root, dados)
        return feitas + 1


def _principal() -> int:
    parser = argparse.ArgumentParser(description='Convites do piloto VLADO.')
    sub = parser.add_subparsers(dest='comando', required=True)
    admin = sub.add_parser('criar-admin')
    admin.add_argument('--nome', required=True)
    admin.add_argument('--dias', type=int, default=90)
    admin.add_argument('--origem', required=True, help='Endereço público, ex.: https://vlado.example.org')
    convite = sub.add_parser('criar-convite')
    convite.add_argument('--nome', required=True)
    convite.add_argument('--casos', required=True, help='IDs separados por vírgula')
    convite.add_argument('--cota', type=int, default=20)
    convite.add_argument('--dias', type=int, default=14)
    convite.add_argument('--origem', required=True)
    sub.add_parser('listar')
    revoga = sub.add_parser('revogar')
    revoga.add_argument('id')
    args = parser.parse_args()
    if args.comando in ('criar-admin', 'criar-convite'):
        if args.comando == 'criar-admin':
            registro, token = criar_convite(ROOT, args.nome, papel='admin', dias=args.dias)
        else:
            registro, token = criar_convite(ROOT, args.nome, casos=[c.strip() for c in args.casos.split(',') if c.strip()],
                                            cota_diaria=args.cota, dias=args.dias)
        print(json.dumps(registro, ensure_ascii=False, indent=2))
        print('Link (mostrado uma única vez):', args.origem.rstrip('/') + '/convite/' + token)
    elif args.comando == 'listar':
        print(json.dumps(listar(ROOT), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(revogar(ROOT, args.id), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(_principal())
    except ValueError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        raise SystemExit(1)
