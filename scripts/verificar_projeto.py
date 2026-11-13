"""Validate active corpus, prompt assembly and bundled file hashes."""
import argparse
import json
from comum import ROOT, conferir_projeto, dentro, ler_json, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pacote', action='store_true', help='Conferir tambem copias de referencia e apoio.')
    args = parser.parse_args()
    result = conferir_projeto()
    if args.pacote:
        records = ler_json(ROOT / 'proveniencia' / 'arquivos_copiados.json')
        for item in records:
            path = dentro(ROOT, item['destino'])
            if not path.is_file() or sha256(path) != item['sha256']:
                raise ValueError(f"Copia ausente ou alterada: {item['destino']}")
        result['copias_conferidas'] = len(records)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('OK de preparacao; nao e validacao da qualidade da apuracao.')


if __name__ == '__main__':
    main()
