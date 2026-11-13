"""Build, search and inspect a round's SQLite index without inference or network."""
import argparse
import json
import sqlite3
import sys

from comum import ROOT
from indice_sqlite import construir_indice, cobertura, ler_passagem, pesquisar, verificar_indice


def main():
    # Stable JSON encoding even when Windows pipes default to a legacy code page.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operacao', required=True)
    for operation in ('construir', 'buscar', 'ler', 'cobertura', 'verificar'):
        command = sub.add_parser(operation)
        command.add_argument('--caso', required=True)
        command.add_argument('--rodada', required=True)
        command.add_argument('--geracao', default='v1')
        if operation == 'buscar':
            query = command.add_mutually_exclusive_group(required=True)
            query.add_argument('--consulta')
            query.add_argument('--consulta-arquivo', help='Arquivo UTF-8 em entrada/; evita interpolar a consulta no shell.')
            command.add_argument('--modo', choices=('comum', 'fts', 'literal'), default='comum')
            command.add_argument('--documentos', nargs='+')
            command.add_argument('--pagina', type=int)
            command.add_argument('--limite', type=int, default=10)
            command.add_argument('--deslocamento', type=int, default=0)
        if operation == 'ler':
            command.add_argument('--referencia', required=True)
    args = parser.parse_args()
    try:
        if args.operacao == 'construir':
            result = construir_indice(ROOT, args.caso, args.rodada, args.geracao)
        elif args.operacao == 'verificar':
            result = verificar_indice(ROOT, args.caso, args.rodada, args.geracao)
        elif args.operacao == 'cobertura':
            result = cobertura(ROOT, args.caso, args.rodada, args.geracao)
        elif args.operacao == 'ler':
            result = ler_passagem(ROOT, args.caso, args.rodada, args.referencia, geracao=args.geracao)
        else:
            query = args.consulta
            if args.consulta_arquivo:
                from pathlib import Path
                from comum import dentro
                relative = Path(args.consulta_arquivo)
                if relative.parts[:1] != ('entrada',):
                    raise ValueError('Arquivo de consulta deve estar em entrada/, relativo ao projeto.')
                query = dentro(ROOT, relative.as_posix()).read_text(encoding='utf-8-sig')
            result = pesquisar(ROOT, args.caso, args.rodada, query, modo=args.modo,
                               documentos=args.documentos, pagina=args.pagina, limite=args.limite,
                               deslocamento=args.deslocamento, geracao=args.geracao)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get('estado') == 'erro_consulta':
            return 2
        return 0
    except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
        print(json.dumps({'estado': 'erro', 'erro': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
