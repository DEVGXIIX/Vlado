# Cadastro antes da pergunta

Implementado em 04/11/2026, versão operacional e prompts **1.2.0**, a pedido do usuário. Cada lote deve ser cadastrado assim que for enviado, antes de qualquer pergunta editorial. O objetivo é contabilizar todos os arquivos recebidos, preservar cópias e evitar que a seleção orientada pela pergunta deixe anexos de fora.

## Na interface

1. Abra `Iniciar pesquisa.cmd`. Em **Cadastrar documentos**, escolha novo caso ou o caso que receberá outro lote.
2. Para um caso novo, informe apenas o nome; o ID é gerado internamente. Indique documentos públicos ou materiais sintéticos e selecione todos os arquivos do envio.
3. Clique em **Enviar e cadastrar agora**. O envio produz imediatamente um recibo por arquivo: nome, ID, hash e condição de novo documento ou duplicata. O inventário mostra o total acumulado do caso, mesmo sem rodada ou pergunta.
4. Confira o número de arquivos do recibo e acrescente outros lotes, se necessário. Só depois envie sua pergunta no Codex, indicando o caso. A seleção no navegador não muda o caso ativo do Codex.

O envio admite até 50 MB e 100 arquivos por lote. O limite de documentos únicos por caso vem da configuração (inicialmente 20). Formatos aceitos: PDF, PNG, JPG/JPEG, TXT, MD, CSV/TSV, XLSX e DOCX. PDFs passam por extração textual automática com `pypdf`, sem OCR. O recibo e o inventário informam o resultado e as páginas sem texto ou com erro. Imagens avulsas e outros formatos continuam sem conversão automática.

O iniciador verifica Python 3.12+, SQLite/FTS5 e `pypdf` no próprio interpretador que abrirá o serviço. A prioridade é `.venv`, runtime do Codex e depois os comandos `python`/`py -3`, sempre com essa verificação. Um Python que apenas responde a `--version` não é suficiente. `Iniciar pesquisa.cmd --verificar-runtime` mostra o ambiente selecionado sem abrir o serviço. Nenhuma dependência é instalada automaticamente.

Se uma instância aberta diretamente estiver sem extrator, a interface informa isso antes do envio; os PDFs recebidos continuam preservados com a falha registrada. O diagnóstico completo fica em **Detalhes técnicos**. Encerre a instância e reabra pelo iniciador atualizado. Para casos ativos com PDFs sem preparação ou com erro, escolha a apuração em **Cadastrar documentos** e use **Preparar PDFs pendentes**, sem reenviar os originais. O botão fica desabilitado se o extrator não estiver disponível. Casos na lixeira precisam ser restaurados explicitamente antes de qualquer preparação.

Se houver formato recusado, arquivo inacessível ou limite excedido, o lote não é confirmado e os arquivos selecionados permanecem na tela para correção. Falha de comunicação deixa o envio sem confirmação: consulte o inventário antes de continuar; reenviar os mesmos bytes identifica duplicatas. Não afirmar recebimento completo quando faltarem itens.

## No chat e nos scripts

O agente deve executar o cadastro ao receber cada lote, sem esperar a pergunta. Não há observador de anexos operando em segundo plano: esse comportamento depende das instruções e da execução pelo agente. Não procurar documentos fora dos anexos/caminhos fornecidos. Se o destino do lote for ambíguo, esclarecer o caso antes de cadastrar.

Na pasta do projeto, com arquivos ilustrativos:

```powershell
python scripts/cadastrar_documentos.py --caso minha_apuracao --novo --titulo "Minha apuração" --natureza publicos --documentos entrada/a.pdf entrada/b.pdf
python scripts/cadastrar_documentos.py --caso minha_apuracao --natureza publicos --documentos entrada/c.pdf
```

`--novo` recusa sobrescrever um caso; sem essa opção, o caso precisa existir. A CLI legada `criar_caso.py` permanece compatível, mas o fluxo atual usa `cadastrar_documentos.py` para ter recibos e acréscimo de lotes. Cadastro não seleciona o caso automaticamente.

## Extração padrão de PDFs

O núcleo compartilhado pelo chat, interface e CLI legada extrai PDFs depois de preservar suas cópias e antes de publicar o lote. Os derivados Markdown ficam em `cadastros/<lote>/derivados/`, vinculados ao mesmo ID do original, com hash de origem, método, página física e linhas da cópia de trabalho. Não são novas fontes independentes. Não há OCR, correção editorial, leitura por IA ou validação de tabelas nessa etapa.

Instale `requirements.txt` no Python que executa o cadastro, ou use o runtime do Codex que já disponha de `pypdf`. Se a dependência faltar, o PDF estiver protegido, inválido ou tiver páginas sem texto/com erro, o original continua cadastrado e o recibo explicita a limitação. Uma falha de gravação ou publicação continua interrompendo o lote. Recepção do arquivo e cobertura textual são estados distintos.

Para preparar PDFs de um caso existente sem reenviar arquivos:

```powershell
python scripts/cadastrar_documentos.py --caso minha_apuracao --preparar-pdfs
```

O comando lê somente as cópias preservadas do caso indicado. Registra uma operação de preparação, sem novos documentos; os campos legados `recebidos`/`duplicados` contam os arquivos existentes processados, não novos anexos enviados. Extrações já preparadas são reutilizadas; falhas podem ser tentadas novamente. Mudanças nos documentos/derivados/metadados incrementam a versão e reiniciam a aprovação do piloto. Rodadas e gerações de índices existentes ficam intactas. O texto passará ao índice da próxima rodada criada após uma pergunta; este comando não cria índice nem rodada.

## Preservação e conferência

- Cada arquivo enviado aparece no recibo, inclusive duplicatas por SHA-256. Bytes iguais usam o ID existente; nomes iguais com bytes diferentes recebem IDs distintos e nunca sobrescrevem originais.
- Novos documentos ou preparação de derivados incrementam a versão do corpus, mantêm os IDs anteriores e reiniciam a aprovação do piloto/teste principal para o corpus alterado. Reenvio só de duplicatas com extração já preparada preserva versão e protocolo, acrescentando o recibo.
- Os originais novos e registros ficam em `casos/<id>/cadastros/<lote>/`: `originais/`, `recibo.json`, `manifesto_cadastrado.json` e, em acréscimos, `manifesto_anterior.json`. O manifesto atual autoriza documentos e registra hashes dos recibos. Arquivos já cadastrados por versões anteriores permanecem nos caminhos anteriores.
- O lote é validado e copiado antes da publicação. A publicação usa troca de metadados e restauração em falhas detectadas; cadastro e congelamento de rodada compartilham uma trava, recusando a segunda operação enquanto a primeira estiver em andamento. Não sobrescrever recibos ou rodadas anteriores.
- Quando a pergunta chegar, `nova_rodada.py` confere integridade e congela documentos, manifesto e recibos da versão atual. Hash divergente ou recibo ausente impede a criação da rodada. A rodada anterior conserva seus documentos e seu índice.

Pendências de anexos conhecidos pelo chat precisam ser resolvidas ou explicitamente excluídas pelo usuário antes de criar a rodada. O script só pode conferir arquivos e recibos que lhe foram informados; não consegue descobrir anexos omitidos pelo operador. O recibo deve ser confrontado com o envio original, não apenas com os arquivos que puderam ser abertos.

O restante do fluxo continua após a pergunta: snapshot, índice da rodada, cobertura, planejamento, pesquisa, cruzamento, revisão e briefing. O cadastro prepara o texto dos PDFs, mas não executa inferência, OCR ou análise editorial. A inferência continua online no Codex e o cadastro não constitui piloto editorial.
