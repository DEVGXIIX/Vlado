"""Register and query structured findings. No inference, OCR or retrospective import."""
import argparse
import json
import sqlite3
import sys

from comum import ROOT, dentro, ler_json
import registros_achados as registros
import indice_achados as indice


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operacao', required=True)
    for operation in ('registrar', 'validar', 'listar', 'construir', 'verificar', 'buscar', 'detalhe', 'evidencia', 'exportar'):
        p = sub.add_parser(operation)
        p.add_argument('--caso', required=True)
        p.add_argument('--rodada', required=True)
        if operation in ('registrar', 'validar'):
            p.add_argument('--arquivo', required=True, help='JSON relativo ao projeto, preparado pelo agente.')
        if operation not in ('registrar', 'validar', 'listar'):
            p.add_argument('--revisao', required=True)
        if operation in ('construir', 'verificar', 'buscar', 'detalhe', 'exportar'):
            p.add_argument('--geracao', required=True, help='Geração do banco de achados; não é a documental.')
        if operation == 'detalhe':
            p.add_argument('--achado-id', required=True)
        if operation == 'evidencia':
            p.add_argument('--evidencia-id', required=True)
        if operation in ('buscar', 'exportar'):
            for name in ('texto', 'documento', 'natureza', 'suporte', 'humana', 'destino', 'briefing'):
                p.add_argument('--' + name)
            p.add_argument('--limite', type=int, default=10)
            p.add_argument('--deslocamento', type=int, default=0)
    a = parser.parse_args()
    try:
        if a.operacao in ('registrar', 'validar'):
            data = ler_json(dentro(ROOT, a.arquivo))
            if a.operacao == 'registrar':
                result = registros.publicar(ROOT, a.caso, a.rodada, data)
            else:
                old = None
                if data.get('anterior'):
                    old, manifest = registros.carregar(ROOT, a.caso, a.rodada, data['anterior']['revisao'])
                    if manifest['registros_sha256'] != data['anterior']['registros_sha256']:
                        raise ValueError('Hash anterior divergente.')
                result = registros.validar(ROOT, a.caso, a.rodada, data, old)
        elif a.operacao == 'listar':
            result = indice.catalogo(ROOT, a.caso, a.rodada)
        elif a.operacao in ('construir', 'verificar'):
            result = getattr(indice, a.operacao)(ROOT, a.caso, a.rodada, a.revisao, a.geracao)
        elif a.operacao == 'detalhe':
            result = indice.detalhe(ROOT, a.caso, a.rodada, a.revisao, a.geracao, a.achado_id)
        elif a.operacao == 'evidencia':
            result = indice.evidencia(ROOT, a.caso, a.rodada, a.revisao, a.evidencia_id)
        else:
            result = indice.consultar(ROOT, a.caso, a.rodada, a.revisao, a.geracao,
                    filtros={k: getattr(a, k) for k in ('texto', 'documento', 'natureza', 'suporte', 'humana', 'destino', 'briefing') if getattr(a, k)},
                    limite=a.limite, deslocamento=a.deslocamento, completa=a.operacao == 'exportar')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'estado': 'erro', 'erro': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
