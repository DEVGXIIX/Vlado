"""Backup and restore of the Mesa's data folders (cases, conversations, rounds, access, settings).

Keys in segredos/ are left out unless --incluir-segredos is given: a pasted key can
be pasted again, and a backup file is easier to leak than a server volume.

  python scripts/backup.py criar --destino backups/
  python scripts/backup.py criar --destino -  > vlado-dados.tar.gz      (stream, e.g. from a container)
  python scripts/backup.py restaurar vlado-dados-AAAAMMDDTHHMMSSZ.tar.gz [--substituir]
  python scripts/backup.py restaurar - [--substituir] < vlado-dados.tar.gz
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PASTAS = ('casos', 'conversas', 'execucoes', 'lixeira', 'entrada', 'acesso', 'ajustes')
SEGREDOS = 'segredos'
MANIFESTO = 'manifesto_backup.json'
PROIBIDOS = (chr(92), ':', chr(0))  # backslash (Windows separator), drive letter, NUL


def _pastas(incluir_segredos: bool) -> tuple[str, ...]:
    return PASTAS + ((SEGREDOS,) if incluir_segredos else ())


def _gravar(root: Path, pacote: tarfile.TarFile, incluir_segredos: bool) -> None:
    incluidas = [p for p in _pastas(incluir_segredos) if (root / p).is_dir()]
    for pasta in incluidas:
        pacote.add(root / pasta, arcname=pasta)
    manifesto = json.dumps({'criado_em_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'pastas': incluidas, 'segredos_incluidos': incluir_segredos}, indent=2).encode('utf-8')
    info = tarfile.TarInfo(MANIFESTO)
    info.size = len(manifesto)
    pacote.addfile(info, io.BytesIO(manifesto))


def criar(root: Path, destino: Path, incluir_segredos: bool = False) -> Path:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / f'vlado-dados-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}.tar.gz'
    with tarfile.open(arquivo, 'x:gz') as pacote:
        _gravar(Path(root), pacote, incluir_segredos)
    return arquivo


def _conferir(membro: tarfile.TarInfo) -> None:
    if membro.name == MANIFESTO and membro.isfile():
        return
    caminho = PurePosixPath(membro.name)
    if (any(c in membro.name for c in PROIBIDOS) or caminho.is_absolute() or '..' in caminho.parts
            or not caminho.parts or caminho.parts[0] not in PASTAS + (SEGREDOS,)
            or not (membro.isfile() or membro.isdir())):
        raise ValueError(f'O backup contém um item fora das pastas de dados: {membro.name!r}. Nada foi restaurado.')


def _extrair(pacote: tarfile.TarFile, membros, destino: Path) -> None:
    for membro in membros:
        if membro.name == MANIFESTO:
            continue
        alvo = destino / PurePosixPath(membro.name)
        if not alvo.resolve().is_relative_to(destino.resolve()):
            raise ValueError(f'O backup contém um item fora das pastas de dados: {membro.name!r}. Nada foi restaurado.')
        if membro.isdir():
            alvo.mkdir(parents=True, exist_ok=True)
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        with pacote.extractfile(membro) as origem, alvo.open('xb') as saida:
            shutil.copyfileobj(origem, saida)


def _restaurar_pacote(root: Path, pacote: tarfile.TarFile, substituir: bool) -> list[str]:
    """Extract into a staging folder, then swap folder by folder; any failure restores the previous data."""
    membros = pacote.getmembers()
    for membro in membros:
        _conferir(membro)
    pastas = sorted({PurePosixPath(m.name).parts[0] for m in membros if m.name != MANIFESTO})
    ocupadas = [p for p in pastas if (root / p).exists() and any((root / p).iterdir())]
    if ocupadas and not substituir:
        raise ValueError(f'O destino já contém dados em {", ".join(ocupadas)}. Use --substituir para trocar por este backup.')
    root.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    preparo = root / f'.restaurando-{marca}'
    trocadas = []
    try:
        preparo.mkdir()
        _extrair(pacote, membros, preparo)
        for pasta in pastas:
            antiga = root / f'.antiga-{pasta}-{marca}'
            if (root / pasta).exists():
                (root / pasta).rename(antiga)
                trocadas.append((pasta, antiga))
            else:
                trocadas.append((pasta, None))
            (preparo / pasta if (preparo / pasta).exists() else preparo / pasta).mkdir(parents=True, exist_ok=True)
            (preparo / pasta).rename(root / pasta)
    except BaseException:
        for pasta, antiga in reversed(trocadas):
            if antiga is not None and antiga.exists():
                if (root / pasta).exists():
                    shutil.rmtree(root / pasta)
                antiga.rename(root / pasta)
            elif antiga is None and (root / pasta).exists():
                shutil.rmtree(root / pasta)
        raise
    finally:
        shutil.rmtree(preparo, ignore_errors=True)
    for _, antiga in trocadas:
        if antiga is not None:
            shutil.rmtree(antiga, ignore_errors=True)
    return pastas


def restaurar(root: Path, arquivo, substituir: bool = False) -> list[str]:
    root = Path(root)
    if arquivo == '-':
        with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()), mode='r:gz') as pacote:
            return _restaurar_pacote(root, pacote, substituir)
    with tarfile.open(arquivo, 'r:gz') as pacote:
        return _restaurar_pacote(root, pacote, substituir)


def _principal() -> int:
    parser = argparse.ArgumentParser(description='Backup dos dados da Mesa de apuração.')
    sub = parser.add_subparsers(dest='comando', required=True)
    cria = sub.add_parser('criar')
    cria.add_argument('--destino', required=True, help='Pasta de destino, ou - para enviar o arquivo à saída padrão')
    cria.add_argument('--incluir-segredos', action='store_true', help='Inclui as chaves de API salvas')
    restaura = sub.add_parser('restaurar')
    restaura.add_argument('arquivo', help='Arquivo .tar.gz, ou - para ler da entrada padrão')
    restaura.add_argument('--substituir', action='store_true', help='Troca os dados atuais pelos do backup')
    args = parser.parse_args()
    if args.comando == 'criar':
        if args.destino == '-':
            with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as pacote:
                _gravar(ROOT, pacote, args.incluir_segredos)
        else:
            print(criar(ROOT, Path(args.destino), args.incluir_segredos))
    else:
        print('Restaurado:', ', '.join(restaurar(ROOT, args.arquivo, args.substituir)), file=sys.stderr)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(_principal())
    except (ValueError, OSError, tarfile.TarError) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        raise SystemExit(1)
