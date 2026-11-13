"""Server-side spend limits: tokens per question and per day for the whole installation.

Values come from configuracao.json "limites" (null disables one limit). The daily
counter lives in ajustes/uso_diario.json (gitignored, Docker volume) and only
keeps the current UTC day.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading

from cadastrar_documentos import _atomico
from comum import ler_json, trava_arquivo

PADROES = {'tokens_por_consulta': 3_000_000, 'tokens_por_dia': 30_000_000}
_TRAVA = threading.Lock()


def hoje() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def ler(root: Path) -> dict:
    try:
        config = ler_json(Path(root) / 'configuracao.json')
    except (OSError, ValueError) as exc:
        raise ValueError('configuracao.json ilegível; não foi possível ler os limites.') from exc
    valores = config.get('limites', {}) if isinstance(config, dict) else None
    if not isinstance(valores, dict) or set(valores) - set(PADROES):
        raise ValueError('"limites" em configuracao.json aceita só tokens_por_consulta e tokens_por_dia.')
    resultado = {**PADROES, **valores}
    for chave, valor in resultado.items():
        if valor is not None and (type(valor) is not int or valor < 1):
            raise ValueError(f'limites.{chave} deve ser um inteiro positivo ou null.')
    return resultado


def _arquivo(root: Path) -> Path:
    return Path(root) / 'ajustes' / 'uso_diario.json'


def _total(root: Path) -> int:
    arquivo = _arquivo(root)
    if not arquivo.is_file():
        return 0
    try:
        dados = json.loads(arquivo.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 0  # a damaged counter must not block the installation; it restarts from zero
    if not isinstance(dados, dict) or dados.get('dia') != hoje():
        return 0
    tokens = dados.get('tokens', 0)
    return tokens if type(tokens) is int and tokens >= 0 else 0


def somar_dia(root: Path, tokens: int) -> int:
    with _TRAVA, trava_arquivo(_arquivo(root)):
        total = _total(root) + max(0, int(tokens))
        arquivo = _arquivo(root)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        _atomico(arquivo, (json.dumps({'dia': hoje(), 'tokens': total}) + '\n').encode('utf-8'))
        return total


def conferir_dia(root: Path) -> None:
    limite = ler(root)['tokens_por_dia']
    if limite is not None and _total(root) >= limite:
        raise ValueError(f'Limite diário de tokens da instalação atingido ({limite}). Novas perguntas voltam amanhã (UTC).')
