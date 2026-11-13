"""Assemble and hash the active prompts; no inference."""
import argparse
from comum import ROOT, conferir_prompts, escrever_json, fluxo_esperado, manifesto_prompts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        conferir_prompts()
        print('OK: fluxo completo e hashes correspondem aos sete modulos.')
    else:
        (ROOT / 'prompts' / 'FLUXO_COMPLETO.md').write_bytes(fluxo_esperado())
        escrever_json(ROOT / 'prompts' / 'manifesto_prompts.json', manifesto_prompts())
        print('Fluxo e manifesto de prompts montados; nenhuma IA foi executada.')


if __name__ == '__main__':
    main()
