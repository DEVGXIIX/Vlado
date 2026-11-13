# Mesa de apuração — 1.0 piloto

Pacote independente para iniciar o piloto em um notebook Windows. Preparado em 10/11/2026, com a interface desktop lapidada e cadastro vazio. Não contém apurações, documentos, respostas, conversas, credenciais ou configurações de conta do computador de preparação.

**Comece por [INSTALAR_NO_NOTEBOOK.md](INSTALAR_NO_NOTEBOOK.md).** Extraia o ZIP inteiro antes de abrir qualquer iniciador.

1. Instale Python 3.12 ou superior e o executável nativo do Codex conforme o guia.
2. Abra **Preparar notebook.cmd**. Ele cria `.venv` nesta pasta e instala as bibliotecas necessárias. A instalação requer internet.
3. Abra **Verificar pacote.cmd** antes do primeiro uso para conferir os arquivos distribuídos.
4. Abra **Abrir mesa.vbs**. Se o Windows não permitir esse iniciador, use **Iniciar pesquisa.cmd**.
5. Na Mesa, crie uma apuração, cadastre os arquivos e confira o recibo. Em **Perguntar ao Codex → Conexão e opções**, entre com sua própria conta ChatGPT.
6. Envie a pergunta apenas quando todos os documentos estiverem conferidos. Revise as fontes e os originais antes de publicar.

## O que está incluído

Cadastro com recibo e extração textual de PDFs, busca SQLite/FTS5 por rodada, conversa com o Codex, achados com conferência humana, caderno editável e exportação, diligências e continuidade com novos documentos. No desktop, há composição recolhível, painel de fontes abaixo do cabeçalho, seletores compactos e paginação retomável. Os ajustes desktop são ativados acima de 1050 px; o layout móvel anterior foi preservado.

**1.0.0-piloto é a versão desta distribuição.** O protocolo técnico e os prompts preservam a versão 1.3.0 da base de desenvolvimento. Não é necessário rebaixar prompts nem reconstruir hashes para instalar.

## Condições de uso

- A análise pelo modelo é online, com os limites e o acesso efetivos da conta ChatGPT. Os arquivos e índices ficam na pasta de trabalho, mas isso não torna a inferência local nem oferece garantias adicionais de sigilo ou retenção.
- A preparação do pacote não é um piloto editorial concluído. Cada caso começa sem aprovação de piloto nem autorização de teste principal.
- Use documentos públicos ou sintéticos durante o piloto. O cadastro não equivale à conferência editorial e não executa OCR.
- O preparador instala também a biblioteca de leitura visual de PDF. A leitura de imagens/tabelas continua exigindo conferência humana; a biblioteca não faz OCR nem checagem factual.
- Este ZIP não inclui Python, Codex, conta, modelos ou bibliotecas já instaladas. Não é uma instalação offline completa.
- Ao começar a trabalhar, preserve a pasta inteira: `casos`, `conversas`, `execucoes` e `lixeira` passam a guardar seus registros. A lixeira da aplicação não libera espaço em disco.

## Guias

- [Instalação e solução de problemas](INSTALAR_NO_NOTEBOOK.md)
- Procedimento do piloto (registro histórico não incluído)
- Cadastro (registro histórico não incluído)
- Interface (registro histórico não incluído)
- Conversa e autenticação (registro histórico não incluído)
- Achados (registro histórico não incluído)
- Caderno editável (registro histórico não incluído)
- Diligências (registro histórico não incluído)
- Validação da distribuição (registro histórico não incluído)

Se preferir operar pelo chat do Codex, abra esta pasta como projeto e use o texto de COMECAR_AQUI.md (registro histórico não incluído). Não há caso ou pauta selecionados antecipadamente.
