"""Confere SHA-256 da distribuição inicial, sem ler documentos de apuração."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def conferir(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / 'manifesto_distribuicao.json').read_text(encoding='utf-8'))
    errors = []
    for item in manifest['arquivos']:
        relative = Path(item['arquivo'])
        target = (root / relative).resolve()
        if relative.is_absolute() or relative.drive or '..' in relative.parts or not target.is_relative_to(root):
            raise ValueError('Manifesto contém caminho fora do pacote.')
        if not target.is_file():
            errors.append({'arquivo':item['arquivo'], 'motivo':'ausente'})
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if target.stat().st_size != item['bytes'] or digest != item['sha256']:
            errors.append({'arquivo':item['arquivo'], 'motivo':'conteúdo divergente'})
    return {'versao':manifest['versao_distribuicao'], 'arquivos_conferidos':len(manifest['arquivos']),
            'estado':'ok' if not errors else 'divergencias', 'divergencias':errors,
            'observacao':'Conferência do pacote inicial; não é validação editorial. Alterações após o uso são esperadas.'}


if __name__ == '__main__':
    try:
        result = conferir()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        raise SystemExit(0 if result['estado'] == 'ok' else 1)
    except (ValueError, OSError, KeyError) as exc:
        print(f'Não foi possível conferir o pacote: {exc}', file=sys.stderr)
        raise SystemExit(1)
