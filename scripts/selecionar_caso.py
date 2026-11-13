"""Select exactly one registered case, or return to no active case."""
import argparse
import re
from comum import ROOT, arquivos_do_corpus, dentro, escrever_json, ler_json


def selecionar(root, case_id=None):
    config=ler_json(root/'configuracao.json')
    if case_id is None:
        config.update(caso_ativo=None,manifesto_ativo=None,estado_inicial='sem_caso_selecionado')
    else:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',case_id):
            raise ValueError('Identificador de caso invalido.')
        catalog=ler_json(root/'casos'/'catalogo.json')
        entry=next((item for item in catalog['casos'] if item['id']==case_id),None)
        if not entry:
            raise ValueError('Caso nao cadastrado.')
        manifest=ler_json(dentro(root,entry['manifesto']))
        if manifest.get('caso_id')!=case_id:
            raise ValueError('ID e manifesto nao correspondem.')
        list(arquivos_do_corpus(root,manifest))
        config.update(caso_ativo=case_id,manifesto_ativo=entry['manifesto'],estado_inicial='caso_selecionado_sem_pergunta')
    escrever_json(root/'configuracao.json',config)
    return config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id')
    group.add_argument('--nenhum',action='store_true')
    args=parser.parse_args()
    config=selecionar(ROOT,args.id)
    print('Caso ativo:',config['caso_ativo'])
    print('Nenhuma apuracao foi executada.')


if __name__=='__main__':
    main()
