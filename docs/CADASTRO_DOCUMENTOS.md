# Cadastro antes da pergunta

Implementado em 04/11/2026, versão operacional e prompts **1.2.0**, a pedido do usuário. Atualizado em 13/11/2026 para versão operacional e prompts **1.4.0**; o cadastro não faz chamadas de modelo. Cada lote deve ser cadastrado assim que for enviado, antes de qualquer pergunta editorial. O objetivo é contabilizar todos os arquivos recebidos, preservar cópias e evitar que a seleção orientada pela pergunta deixe anexos de fora.

## Na interface

1. Abra `Iniciar pesquisa.cmd`. Em **Cadastrar documentos**, escolha novo caso ou o caso que receberá outro lote.
2. Para um caso novo, informe apenas o nome; o ID é gerado internamente. Indique documentos públicos ou materiais sintéticos e selecione todos os arquivos do envio.
3. Clique em **Enviar e cadastrar agora**. O envio produz imediatamente um recibo por arquivo: nome, ID, hash e condição de novo documento ou duplicata. O inventário mostra o total acumulado do caso, mesmo sem rodada ou pergunta.
4. Confira o número de arquivos do recibo e acrescente outros lotes, se necessário. Só depois envie sua pergunta na conversa da Mesa (ou ao agente de chat), indicando o caso. A seleção no navegador não muda o caso ativo do Codex.

O envio admite até 50 MB e 100 arquivos por lote. O limite de documentos únicos por caso vem da configuração (inicialmente 20). Formatos aceitos: PDF, PNG, JPG/JPEG, TXT, MD, CSV/TSV, XLSX e DOCX. PDFs passam por extração textual automática com `pypdf` e, nas páginas sem texto nativo utilizável, por OCR local. O recibo e o inventário informam o resultado: páginas com texto nativo, reconhecidas por OCR, sem texto e com falha. Imagens avulsas e outros formatos continuam sem conversão automática.

O iniciador verifica Python 3.12+, SQLite/FTS5 e `pypdf` (o OCR é opcional e informado à parte) no próprio interpretador que abrirá o serviço. A prioridade é `.venv`, runtime do Codex e depois os comandos `python`/`py -3`, sempre com essa verificação. Um Python que apenas responde a `--version` não é suficiente. `Iniciar pesquisa.cmd --verificar-runtime` mostra o ambiente selecionado sem abrir o serviço. Nenhuma dependência é instalada automaticamente.

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

O núcleo compartilhado pelo chat, interface e CLI legada extrai PDFs depois de preservar suas cópias e antes de publicar o lote. Os derivados Markdown ficam em `cadastros/<lote>/derivados/`, vinculados ao mesmo ID do original, com hash de origem, método, página física e linhas da cópia de trabalho. Não são novas fontes independentes. Não há correção editorial, leitura por IA ou validação de tabelas nessa etapa.

Instale `requirements.txt` no Python que executa o cadastro, ou use o runtime do Codex que já disponha de `pypdf`. Se a dependência faltar, o PDF estiver protegido, inválido ou tiver páginas sem texto/com erro, o original continua cadastrado e o recibo explicita a limitação. Uma falha de gravação ou publicação continua interrompendo o lote. Recepção do arquivo e cobertura textual são estados distintos.

Para preparar PDFs de um caso existente sem reenviar arquivos:

```powershell
python scripts/cadastrar_documentos.py --caso minha_apuracao --preparar-pdfs
```

O comando lê somente as cópias preservadas do caso indicado. Registra uma operação de preparação, sem novos documentos; os campos legados `recebidos`/`duplicados` contam os arquivos existentes processados, não novos anexos enviados. Extrações já preparadas são reutilizadas, exceto páginas sem texto ainda não submetidas ao OCR ou com falha de OCR, que são reprocessadas se houver motor; falhas de extração podem ser tentadas novamente. Mudanças nos documentos/derivados/metadados incrementam a versão e reiniciam a aprovação do piloto. Rodadas e gerações de índices existentes ficam intactas. O texto passará ao índice da próxima rodada criada após uma pergunta; este comando não cria índice nem rodada.

## OCR local de páginas digitalizadas

O texto nativo do PDF sempre tem prioridade. O OCR só é aplicado às páginas em que o `pypdf` não obtém texto utilizável (menos de 10 caracteres alfanuméricos, como uma página só com imagem ou só com um número carimbado). Nada é enviado a serviço externo e nenhum modelo de linguagem é chamado: o reconhecimento roda nesta máquina.

- **Motor principal:** OCRmyPDF (`--force-ocr --rotate-pages --sidecar`, restrito às páginas sem texto, saída PDF descartada) com Tesseract e Ghostscript. Idioma padrão `por+eng`.
- **Alternativa:** se o OCRmyPDF ou o Ghostscript faltarem (ou o OCRmyPDF falhar), o PyMuPDF renderiza a página a 300 dpi e a CLI do Tesseract a reconhece; a orientação é detectada com o OSD do Tesseract (`osd.traineddata`) e corrigida só na imagem.
- **Original intacto:** o PDF original é copiado byte a byte (hash inalterado). O texto reconhecido entra no mesmo derivado paginado `D###_texto_pdf.md`, com a página física do original, de modo que o índice SQLite/FTS5 e o leitor de fontes o usem sem mudanças e as citações abram a página correta do original.
- **Origem por página:** o cabeçalho do derivado lista `texto_nativo` ou `ocr` por página; o manifesto guarda o mesmo em `paginas_origem` do derivado e, em `extracao_pdf`, `paginas_texto_nativo`, `paginas_ocr`, `paginas_sem_texto`, `paginas_com_erro` (com `etapa` `extracao` ou `ocr`), `ocr_tentado` e `ocr_motor` (motor, versões do OCRmyPDF/Tesseract/Ghostscript ou PyMuPDF e idiomas realmente usados). O resumo do recibo traz as contagens (`paginas_texto_nativo`, `paginas_ocr`, `paginas_sem_texto`, `paginas_com_erro`, `protegidos`).
- **PDF protegido por senha:** não é lido nem reconhecido; o original é preservado e o recibo indica `protegido` (estado `erro`).
- **Reprocessar o que já está cadastrado:** `python scripts/cadastrar_documentos.py --caso ID --preparar-pdfs` aplica OCR aos PDFs cujas páginas sem texto ainda não passaram por OCR (ou cujo OCR falhou) e publica uma **nova versão do corpus**, com novo derivado que substitui o anterior no manifesto atual (`substitui_sha256`). Rodadas e índices anteriores permanecem intactos; o OCR concluído não é repetido.

Variáveis de ambiente (lidas pelo processo que executa o cadastro):

| Variável | Efeito | Padrão |
|---|---|---|
| `VLADO_OCR=0` | desliga o OCR (o PDF fica como antes, com páginas sem texto) | ligado |
| `VLADO_OCR_IDIOMAS` | idiomas do Tesseract, ex.: `por+eng` | `por+eng` |
| `VLADO_TESSERACT` | caminho do executável do Tesseract | `PATH`, depois `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `VLADO_TESSDATA` | pasta com os `*.traineddata` (`por`, `eng`, `osd`) | `%LOCALAPPDATA%\vlado\tessdata`, se existir |
| `VLADO_OCR_MOTOR` | `auto`, `ocrmypdf` ou `tesseract` | `auto` |
| `VLADO_OCR_TIMEOUT` | segundos por página antes de abortar o processo | 180 |

Os subprocessos rodam sem abrir janelas de console no Windows, com saída capturada e tempo limite. No Docker, `Dockerfile` instala `tesseract-ocr`, `-por`, `-eng`, `-osd`, `ghostscript`, `pngquant` e `unpaper`, e `requirements.txt` fixa `ocrmypdf==16.10.4`. No Windows o Ghostscript não é obrigatório: sem ele, a alternativa PyMuPDF + Tesseract é usada automaticamente. Se nenhum motor estiver disponível, o cadastro segue como antes e o recibo informa `ocr_indisponivel`.

Limites: OCR não é perfeito. Pode errar letras, números, nomes, tabelas, manuscritos, carimbos e colunas, e trocar a ordem de leitura. O recibo e a cobertura do índice não atestam fidelidade: confira sempre a página no original antes de usar uma passagem como evidência. O OCR roda durante o cadastro e pode levar segundos por página; PDFs grandes alongam a requisição. Imagens avulsas (PNG/JPG) não passam por OCR.

## Preservação e conferência

- Cada arquivo enviado aparece no recibo, inclusive duplicatas por SHA-256. Bytes iguais usam o ID existente; nomes iguais com bytes diferentes recebem IDs distintos e nunca sobrescrevem originais.
- Novos documentos ou preparação de derivados incrementam a versão do corpus, mantêm os IDs anteriores e reiniciam a aprovação do piloto/teste principal para o corpus alterado. Reenvio só de duplicatas com extração já preparada preserva versão e protocolo, acrescentando o recibo.
- Os originais novos e registros ficam em `casos/<id>/cadastros/<lote>/`: `originais/`, `recibo.json`, `manifesto_cadastrado.json` e, em acréscimos, `manifesto_anterior.json`. O manifesto atual autoriza documentos e registra hashes dos recibos. Arquivos já cadastrados por versões anteriores permanecem nos caminhos anteriores.
- O lote é validado e copiado antes da publicação. A publicação usa troca de metadados e restauração em falhas detectadas; cadastro e congelamento de rodada compartilham uma trava, recusando a segunda operação enquanto a primeira estiver em andamento. Não sobrescrever recibos ou rodadas anteriores.
- Quando a pergunta chegar, `nova_rodada.py` confere integridade e congela documentos, manifesto e recibos da versão atual. Hash divergente ou recibo ausente impede a criação da rodada. A rodada anterior conserva seus documentos e seu índice.

Pendências de anexos conhecidos pelo chat precisam ser resolvidas ou explicitamente excluídas pelo usuário antes de criar a rodada. O script só pode conferir arquivos e recibos que lhe foram informados; não consegue descobrir anexos omitidos pelo operador. O recibo deve ser confrontado com o envio original, não apenas com os arquivos que puderam ser abertos.

O restante do fluxo continua após a pergunta: snapshot, índice da rodada, cobertura, planejamento, pesquisa, cruzamento, revisão e briefing. O cadastro prepara o texto dos PDFs (nativo ou por OCR local), mas não executa inferência nem análise editorial. A inferência ocorre online, pela API do provedor configurado, somente depois da pergunta. O cadastro não constitui piloto editorial.
