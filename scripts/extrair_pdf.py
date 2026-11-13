"""Extract a PDF to page/line text, preserving empty/error pages without OCR."""
import argparse
from pathlib import Path
from comum import sha256

SEM_TEXTO = '[SEM TEXTO EXTRAIVEL NESTA PAGINA]'
ERRO_TEXTO = '[ERRO DE EXTRACAO NESTA PAGINA]'


def extrair_pdf(source: Path, identifier: str, target: Path) -> dict:
    """Return an explicit extraction outcome; storage failures still abort registration."""
    if target.exists():
        raise FileExistsError('Nao sobrescrever extracao existente; usar nova versao.')
    result = {'estado': 'erro', 'paginas_pdf': None, 'paginas_com_texto': 0,
              'paginas_sem_texto': [], 'paginas_com_erro': [], 'ocr': False,
              'conferencia_humana': 'nao_realizada', 'metodo': None}
    # Catch PDF/dependency errors only. Do not disguise a failed write as a readable original.
    try:
        import pypdf
        result['metodo'] = f'pypdf {pypdf.__version__}; extract_text por pagina; sem OCR ou correcao editorial.'
        reader = pypdf.PdfReader(source)
        if reader.is_encrypted and not reader.decrypt(''):
            raise ValueError('PDF protegido por senha; texto nao extraido.')
        count = len(reader.pages)
        if count == 0:
            raise ValueError('PDF sem paginas; texto nao extraido.')
        result['paginas_pdf'] = count
    except ImportError:
        result['mensagem'] = 'pypdf indisponivel neste Python; instalar as dependencias de requirements.txt ou usar o runtime do Codex.'
        return result
    except Exception as exc:
        result['mensagem'] = f'{type(exc).__name__}: {str(exc)[:1000]}'
        return result

    parts = [f'# {identifier} - copia textual de trabalho', '',
             f'Original: {source.name}', f'SHA-256 do PDF: {sha256(source)}',
             f'Metodo: {result["metodo"]}',
             'Pagina = posicao fisica no PDF. Linhas = copia de trabalho, nao o original.', '']
    for number in range(1, count + 1):
        parts.extend([f'## {identifier} - pagina PDF {number}', ''])
        try:
            text = reader.pages[number - 1].extract_text() or ''
        except Exception as exc:
            result['paginas_com_erro'].append({'pagina_pdf': number,
                                              'erro': f'{type(exc).__name__}: {str(exc)[:1000]}'})
            parts.extend([ERRO_TEXTO, ''])
            continue
        if text.strip():
            result['paginas_com_texto'] += 1
            parts.extend(f'[L{line:04d}] {content}'
                         for line, content in enumerate(text.splitlines(), 1))
        else:
            result['paginas_sem_texto'].append(number)
            parts.append(SEM_TEXTO)
        parts.append('')
    if result['paginas_com_erro']:
        result['estado'] = 'parcial' if result['paginas_com_texto'] else 'erro'
    elif result['paginas_sem_texto']:
        result['estado'] = 'parcial' if result['paginas_com_texto'] else 'sem_texto'
    else:
        result['estado'] = 'extraido'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(parts))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--saida', required=True)
    args = parser.parse_args()
    source, target = Path(args.pdf), Path(args.saida)
    import json
    result = extrair_pdf(source, args.id, target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['estado'] == 'erro' else 0


if __name__ == '__main__':
    raise SystemExit(main())
