"""Distribuição vazia do piloto, por lista permitida; nunca lê acervos existentes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'empacotamento/piloto_1_0'
GUIDES = ('APURACAO', 'ACHADOS_IA', 'BANCO_SQLITE', 'CADASTRO_DOCUMENTOS', 'CADERNO_APURACAO',
          'CONTINUIDADE_DOCUMENTAL', 'DILIGENCIAS', 'FLUXO_AUTOMATICO_CODEX', 'INTEGRACAO_CODEX',
          'INTERFACE_PESQUISA', 'PILOTO')


def write(root, name, text):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')


def json_file(root, name, value):
    write(root, name, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def copy(root, relative):
    source = ROOT / relative
    if not source.resolve().is_relative_to(ROOT) or source.is_symlink():
        raise ValueError('Entrada fora do projeto ou link simbólico: ' + relative)
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def assemble(output):
    output.mkdir(parents=True, exist_ok=False)
    for name in ('AGENTS.md', 'COMECAR_AQUI.md', 'requirements.txt', 'requirements-opcional.txt',
                 '.gitignore', 'Abrir mesa.vbs', 'Iniciar pesquisa.cmd'):
        copy(output, name)
    for folder in ('interface', 'prompts', 'modelos'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                copy(output, path.relative_to(ROOT).as_posix())
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        if path.name != Path(__file__).name:
            copy(output, path.relative_to(ROOT).as_posix())
    copy(output, 'scripts/README.md')
    for path in sorted((ROOT / 'testes').glob('*')):
        if path.is_file() and path.suffix in ('.py', '.cjs'):
            copy(output, path.relative_to(ROOT).as_posix())
    for path in sorted((ROOT / 'testes/fixtures').glob('*.json')):
        copy(output, path.relative_to(ROOT).as_posix())
    for name in GUIDES:
        copy(output, f'docs/{name}.md')
    for path in sorted(TEMPLATES.iterdir()):
        relative = 'scripts/' + path.name if path.suffix == '.py' else path.name
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    # Identity of the distribution is distinct from the unchanged prompt protocol.
    config = json.loads((ROOT / 'configuracao.json').read_text(encoding='utf-8'))
    config.update(versao='1.0.0-piloto', versao_base='1.3.0', caso_ativo=None, manifesto_ativo=None,
                  modelo_observado=None, estado_inicial='sem_caso_selecionado')
    json_file(output, 'configuracao.json', config)
    json_file(output, 'casos/catalogo.json', {'casos':[]})
    json_file(output, 'lixeira/registro.json', {'versao':1, 'itens':[]})
    for name in ('casos', 'conversas', 'execucoes', 'entrada', 'lixeira'):
        write(output, name + '/README.md', '# ' + name.capitalize() + '\n\nPasta inicialmente vazia nesta distribuição. Os registros serão criados durante o uso, por apuração. Preserve a pasta inteira ao fazer backup.\n')
    write(output, 'requirements-piloto.txt', '# Dependências da distribuição piloto, incluindo leitura visual de PDF sem OCR.\n-r requirements.txt\nPyMuPDF>=1.24,<2\n')
    write(output, 'ESTADO_ATUAL.md', '# Estado inicial — 1.0 piloto\n\nDistribuição 1.0.0-piloto; base e prompts 1.3.0. Nenhum caso ativo, documento recebido, conversa ou rodada. Preparado para iniciar o piloto, sem aprovação editorial ou autorização de teste principal. Leia README.md e INSTALAR_NO_NOTEBOOK.md.\n')
    write(output, 'RETOMAR_NO_CODEX.txt', 'Abra esta pasta como projeto. Leia AGENTS.md, README.md e ESTADO_ATUAL.md. Não há pergunta editorial nem caso ativo. Aguarde documentos e cadastre cada lote antes da pergunta.\n')
    write(output, 'docs/DESKTOP_PILOTO.md', '# Interface desktop do piloto\n\nAcima de 1050 px, a composição pode ser recolhida sem descartar rascunhos, o painel de fontes fica abaixo do cabeçalho, seletores são resumidos após escolha explícita, a paginação é retomável e o caderno usa texto de 16 px. Abaixo desse breakpoint, os controles anteriores são preservados. Rascunhos ainda ficam na memória da página: salvar notas e confirmar o envio são ações distintas de recolher a composição.\n')
    write(output, 'proveniencia/README.md', '# Procedência da distribuição\n\nCópia funcional selecionada da base de desenvolvimento 1.3.0, preparada como distribuição 1.0.0-piloto. O código da aplicação e o protocolo de prompts foram preservados; configuração inicial, apresentação da versão, preparador e documentação de instalação foram preparados para o piloto. Não inclui o repositório de referência, corpora, resultados ou credenciais do ambiente de desenvolvimento. As licenças das fontes tipográficas estão em interface/fonts.\n')
    html = (output / 'interface/index.html').read_text(encoding='utf-8')
    html = html.replace('<title>Mesa de apuração</title>', '<title>Mesa de apuração — 1.0 piloto</title>')
    write(output, 'interface/index.html', html)
    for name in ('INTEGRACAO_CODEX', 'INTERFACE_PESQUISA'):
        path = output / f'docs/{name}.md'
        write(output, f'docs/{name}.md', '> Guia técnico da base 1.3.0. A distribuição 1.0 piloto começa vazia; verificações históricas descritas abaixo não equivalem a testes no notebook. Consulte INSTALAR_NO_NOTEBOOK.md e DESKTOP_PILOTO.md.\n\n' + path.read_text(encoding='utf-8'))
    readme = output / 'scripts/README.md'
    write(output, 'scripts/README.md', readme.read_text(encoding='utf-8') + '\nNesta distribuição, confira os arquivos com `conferir_pacote.py`. O modo legado `verificar_projeto.py --pacote` depende de cópias de referência não incluídas neste piloto.\n')


def command(output, args, name):
    result = subprocess.run([sys.executable, *args], cwd=output, capture_output=True, encoding='utf-8', errors='replace')
    log = result.stdout + result.stderr
    log = log.replace(str(ROOT), '<PROJETO_DE_PREPARACAO>').replace(str(output), '<PACOTE>').replace(sys.executable, '<PYTHON_DE_VALIDACAO>')
    write(output, 'validacao/' + name + '.txt', log)
    if result.returncode:
        raise RuntimeError(f'Falhou {name}; consulte {output / "validacao" / (name + ".txt")}')
    return result.stdout + result.stderr


def smoke(output):
    # New process prevents importing application modules from the source workspace.
    code = '''import http.client,json,threading
from interface_pesquisa import Servidor
from pathlib import Path
server=Servidor(('127.0.0.1',0),Path.cwd())
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    checks={}
    for path in ('/','/desktop.js','/api/catalogo'):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        conn.request('GET',path);res=conn.getresponse();body=res.read();conn.close()
        assert res.status==200,(path,res.status)
        if path=='/api/catalogo': assert json.loads(body)['casos']==[]
        checks[path]=res.status
    assert server.conversas.rpc is None
    print(json.dumps({'http':checks,'cadastro_vazio':True,'modelo_iniciado':False}))
finally:
    server.shutdown();server.server_close()
'''
    # The launcher imports from this copy's scripts directory.
    bootstrap = "import sys;sys.path.insert(0,'scripts');" + code
    return command(output, ['-c', bootstrap], 'abertura_interface')


def clean_links(output):
    # Historical QA references are not shipped. Keep their labels without broken links.
    pattern = re.compile(r'\[([^\]\n]+)\]\(([^)\n]+)\)')
    for path in output.rglob('*.md'):
        if path.parts[len(output.parts)] in ('prompts', 'testes'):
            continue
        def replace(match):
            url = match.group(2)
            if re.match(r'^[a-zA-Z]+:', url) or url.startswith('#'):
                return match.group(0)
            target = (path.parent / unquote(url.split('#')[0])).resolve()
            return match.group(0) if target.exists() else match.group(1) + ' (registro histórico não incluído)'
        original = path.read_text(encoding='utf-8')
        updated = pattern.sub(replace, original)
        if original != updated:
            path.write_text(updated, encoding='utf-8', newline='\n')


def inventory(output):
    forbidden = {'__pycache__', '.venv', '.codex', '.aws', '.git', 'referencia_original'}
    entries = []
    for path in sorted(output.rglob('*')):
        rel = path.relative_to(output)
        if not path.is_file() or path.suffix == '.pyc' or forbidden.intersection(rel.parts):
            continue
        if rel.as_posix() == 'manifesto_distribuicao.json':
            continue
        if rel.parts[0] in ('casos', 'conversas', 'execucoes', 'entrada', 'lixeira') and rel.as_posix() not in {
            'casos/catalogo.json', 'lixeira/registro.json', *[f'{folder}/README.md' for folder in ('casos','conversas','execucoes','entrada','lixeira')]}:
            raise ValueError('Estado editorial inesperado no pacote: ' + rel.as_posix())
        entries.append({'arquivo':rel.as_posix(), 'bytes':path.stat().st_size,
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=ROOT / 'distribuicao/Apuracao-1.0-piloto')
    args = parser.parse_args()
    output = args.saida.resolve()
    archive = output.with_suffix('.zip')
    # with_suffix would remove .0-piloto from the distribution name; append instead.
    archive = output.parent / (output.name + '.zip')
    if output == ROOT or not output.is_relative_to(ROOT) or output.exists() or archive.exists():
        raise ValueError('Escolha uma pasta nova dentro do projeto; nada será sobrescrito.')
    assemble(output)
    print('Cópia vazia montada; executando verificações...', flush=True)
    command(output, ['scripts/montar_fluxo.py','--check'], 'prompts')
    command(output, ['scripts/verificar_projeto.py'], 'projeto')
    tests = command(output, ['-m','unittest','discover','-s','testes','-v'], 'testes')
    smoke(output)
    count = re.search(r'Ran (\d+) tests?', tests)
    report = {'distribuicao':'1.0.0-piloto', 'prompts':'1.3.0', 'testes':int(count.group(1)) if count else None,
              'testes_aprovados':True, 'interface_http':True, 'sem_caso_ativo':True,
              'instalacao_no_notebook_testada':False, 'instalacao_pip_executada':False,
              'inferencias_executadas':0, 'data_local':'2026-11-10'}
    json_file(output, 'validacao/resumo.json', report)
    write(output, 'docs/VERIFICACAO.md', '# Verificação da distribuição 1.0 piloto\n\n' +
          f'Em 10/11/2026, fluxo e integridade inicial passaram, assim como {report["testes"]} testes automatizados na cópia de distribuição. O servidor abriu com cadastro vazio e serviu HTML e desktop.js sem iniciar processo de modelo.\n\n' +
          'A instalação por pip, o login e o funcionamento no notebook de destino ainda precisam ser verificados nele. Python e Codex não estão incluídos. Esta preparação não é piloto editorial nem aprovação humana.\n\n' +
          'Consulte os registros em [validacao](../validacao/resumo.json). As verificações anteriores da base não foram transportadas como resultados desta distribuição.\n')
    clean_links(output)
    entries = inventory(output)
    json_file(output, 'manifesto_distribuicao.json', {'versao_distribuicao':'1.0.0-piloto', 'versao_base':'1.3.0',
        'versao_prompts':'1.3.0', 'data_local':'2026-11-10', 'preparado_em_utc':datetime.now(timezone.utc).isoformat(),
        'plataforma':'Windows', 'estado':'preparado_para_piloto', 'piloto_editorial_realizado':False,
        'casos_incluidos':0, 'conversas_incluidas':0, 'credenciais_incluidas':False,
        'observacao':'O próprio manifesto não está na sua lista de hashes. Confira também o SHA-256 do ZIP fornecido ao lado.',
        'arquivos':entries})
    result = subprocess.run([sys.executable, str(output / 'scripts/conferir_pacote.py')], capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for relative in ['manifesto_distribuicao.json', *[item['arquivo'] for item in entries]]:
            bundle.write(output / relative, output.name + '/' + relative)
    # Verify the transferred bytes after extraction into another path.
    with tempfile.TemporaryDirectory(prefix='piloto_extraido_') as temp:
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            bundle.extractall(temp)
        extracted = Path(temp) / output.name
        verified = subprocess.run([sys.executable, str(extracted / 'scripts/conferir_pacote.py')], capture_output=True, text=True, encoding='utf-8')
        if verified.returncode:
            raise RuntimeError('A conferência da cópia extraída falhou: ' + verified.stdout + verified.stderr)
        checked = subprocess.run([sys.executable, str(extracted / 'scripts/montar_fluxo.py'),'--check'], capture_output=True, text=True, encoding='utf-8')
        if checked.returncode:
            raise RuntimeError('A cópia extraída não confere o fluxo.')
        smoke(extracted)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    write(archive.parent, archive.name + '.sha256', digest + '  ' + archive.name + '\n')
    print(json.dumps({'pasta':str(output), 'zip':str(archive), 'bytes':archive.stat().st_size,
                      'sha256':digest, 'arquivos':len(entries) + 1, 'testes':report['testes'],
                      'zip_extraido_e_conferido':True}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
