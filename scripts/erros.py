"""Stable error codes for the interface to translate. The Portuguese messages stay as they are.

Each HTTP error answer carries `codigo` (and `parametros` when the message has numbers the
interface needs). Codes are part of the contract with the interface: rename only together with it.
No model or network calls.
"""
from __future__ import annotations

import json
import re

# Order matters: the first pattern that matches the message wins.
PADROES: tuple[tuple[str, str], ...] = (
    ('endereco_nao_autorizado', r'^Endereço não autorizado'),
    ('sessao_expirada', r'^Sessão expirada ou convite revogado'),
    ('acesso_indisponivel', r'^Registro de acesso (indisponível|ilegível)'),
    ('origem_nao_autorizada', r'^Origem ou sessão não autorizada'),
    ('operacao_inexistente', r'^Operação não encontrada'),
    ('pagina_inexistente', r'^Página não encontrada'),
    ('requisicao_invalida', r'^Requisição (vazia ou muito grande|deve ser um objeto JSON)'),
    ('operacao_proibida', r'^Operação não permitida'),
    ('servico_nao_encerravel', r'^O serviço hospedado não pode ser encerrado'),
    ('caso_nao_liberado', r'^Apuração não liberada para este convite'),
    ('campos_nao_permitidos', r'^Convidados enviam somente'),
    ('convite_invalido', r'^Convite inválido'),
    ('cota_diaria_esgotada', r'^Limite diário de (?P<cota>\d+) pergunta'),
    ('limite_tokens_dia', r'^Limite diário de (tokens|uso) da instalação'),
    ('limite_tokens_consulta', r'^(Limite de tokens por consulta atingido|O limite de tokens por consulta)'),
    ('pergunta_em_andamento', r'^Já há uma pergunta em andamento'),
    ('conversa_indisponivel', r'^Conversa indisponível para este acesso'),
    ('conversa_invalida', r'^Conversa inválida'),
    ('conversa_em_execucao', r'^(Esta conversa está em execução|Esta conversa já tem uma execução ativa|'
                             r'A conversa de origem está em execução)'),
    ('execucao_em_andamento', r'^Há uma execução em andamento'),
    ('conversa_concluida', r'^Esta pergunta já foi concluída e publicada'),
    ('conversa_nao_retomavel', r'^(Esta conversa não tem uma execução interrompida|A pergunta não chegou a ser congelada|'
                               r'A etapa \w+ publicou a revisão)'),
    ('pergunta_invalida', r'^Informe uma pergunta'),
    ('chave_ausente', r'^Chave de API ausente'),
    ('caso_nao_selecionado', r'^Selecione um caso'),
    ('cursor_invalido', r'^Cursor/espera inválidos'),
    ('cursor_posterior', r'^Cursor posterior ao histórico'),
    ('caso_invalido', r'^Identificador de caso inv[aá]lido'),
    ('apuracao_inexistente', r'^Apuração não encontrada'),
    ('chave_formato_invalido', r'^Chave de API em formato inválido'),
    ('revisao_ia_mudou', r'^A revisão da IA mudou'),
    ('marcacao_alterada', r'^A marcação foi alterada em outra janela'),
    ('achado_fora_da_revisao', r'^Achado ou versão fora desta revisão'),
    ('achado_sem_fontes', r'^Este achado não tem fontes vinculadas'),
    ('id_invalido', r'^ID de (evidência|achado) inválido'),
    ('nome_confirmacao_divergente', r'^Digite o nome do item'),
    ('conferencia_sem_original', r'^Para marcar “Conferida no original”'),
    ('falha_leitura', r'^Falha ao ler arquivos do servidor'),
)
_COMPILADOS = tuple((codigo, re.compile(padrao)) for codigo, padrao in PADROES)


def codigo_de(mensagem: str, exc: BaseException | None = None) -> tuple[str, dict]:
    """(codigo, parametros) for an error message; ErroIA falls back to 'ia_<its code>'."""
    for codigo, padrao in _COMPILADOS:
        achado = padrao.search(mensagem or '')
        if achado:
            parametros = {k: int(v) if v.isdigit() else v for k, v in achado.groupdict().items() if v is not None}
            return codigo, parametros
    if isinstance(exc, json.JSONDecodeError):
        return 'json_invalido', {}
    codigo_ia = getattr(exc, 'codigo', None)
    if isinstance(codigo_ia, str) and re.fullmatch(r'[a-z_]{1,40}', codigo_ia):
        return 'ia_' + codigo_ia, {}
    return 'erro', {}
