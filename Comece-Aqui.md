# VLADO — briefing para preparar o primeiro piloto do Intercept

## 1. Sua tarefa

Você é a IA de desenvolvimento encarregada de retomar o VLADO e preparar a primeira entrega para o Intercept. Leia o repositório, reproduza o que for possível em uma cópia limpa e escolha as tecnologias do piloto com base no código, nos requisitos e nos recursos disponíveis. Proponha uma escolha principal para cada decisão, justifique-a e organize a implementação em ordem de execução. Registre as premissas que dependem de confirmação do grupo. Avance com tarefas reversíveis e com testes sintéticos enquanto as dependências externas são confirmadas.

O VLADO é um protótipo de estudantes de Jornalismo da UNESP Bauru para ajudar pequenas redações e veículos independentes a consultar documentos, encontrar passagens relevantes e conferir cada achado no original. O projeto acadêmico `NHagar/semantic-search-assistant` orientou a divisão da apuração em etapas. O Epstein Files Engine inspirou o caminho da busca à fonte primária. [Migração e procedência](MIGRACAO.md)

**Entrega principal.** Um piloto online sob administração do grupo, acessível por link restrito no navegador. A interface, as instruções e a resposta da demonstração devem estar em inglês. Os convidados consultam um acervo público previamente carregado e chegam ao trecho e à página do original. O grupo administra a ingestão e o acesso. O uso local da versão existente fica disponível como alternativa de demonstração e desenvolvimento.

## 2. Estado verificado da base

- **Código de partida.** A versão 1.3.0 foi publicada em `Palhunto/Vlado`, na branch `main`, no commit `ff816bd81d80583fb8953a4529868ea6d3840320`. O clone começa com catálogo vazio e seleção global nula. O pacote de migração contém o mesmo commit, instaladores Windows, o handoff interno e os registros de validação fora do repositório. Use esse commit como referência e compare-o com o estado atual do remoto ao retomar. [Repositório e commit de partida](https://github.com/Palhunto/Vlado/commit/ff816bd81d80583fb8953a4529868ea6d3840320)
- **Origem e diferenças locais.** A pasta de desenvolvimento que antecedeu a publicação estava sem metadados Git e tinha um caso de teste selecionado. A importação levou o código operacional, incluindo marca VLADO, tema, ajustes de usabilidade, publicação canônica, continuidade, caderno, diligências e exportação. Documentos, conversas e rodadas de trabalho ficaram na origem. O SHA `0d5fa4cbe2c98e9c961a16c52a47d7bc0d708f6c` identifica o projeto acadêmico de referência. [Proveniência](../proveniencia/origem_repositorio.json)
- **Verificado no pacote publicado.** Os 165 testes automatizados passaram. A cópia extraída e o clone local preservaram os arquivos verificados. O servidor respondeu em HTTP com catálogo vazio, sem iniciar o modelo. A instalação, as credenciais e o funcionamento na estação ou hospedagem de destino precisam ser conferidos no ambiente escolhido.
- **Execução online histórica.** Em 06/11, o runtime da aplicação informou `gpt-5.6-sol` em um teste com ata e boletim fictícios. Duas rodadas na mesma conversa completaram as seis etapas e publicaram achados verificáveis em `r3_sintese/g1`. A demo preparada mostrou como abrir a linha 2 da ata e registrar a conferência humana à parte. Ensaios anteriores com três fatos relevantes da Americanas verificaram a persistência de fontes e de um complemento. Essas rodadas históricas ainda usavam um fluxo sem publicação canônica. [Fluxo e registros técnicos](FLUXO_AUTOMATICO_CODEX.md)
- **Identificado no código.** Há cadastro, extração textual de PDF, busca, leitor de originais, conferência humana, comparativo entre versões, caderno, diligências e exportação. Os testes técnicos verificaram os contratos de integração. A qualidade editorial de um novo resultado, a escala de redação e o ganho de tempo continuam por medir.
- **Relatado pelo grupo.** Duy gostou do protótipo e pediu uma versão em inglês para compartilhar com colegas de redações independentes. As prioridades registradas pela equipe foram facilitar a conferência e o seguimento da apuração. Confirme com o grupo o contato, a janela do teste e o retorno esperado do Intercept. O relato da reunião orienta o piloto e deve ser atribuído à equipe se for citado.

### O que ler primeiro

1. `AGENTS.md`, `README.md`, `ESTADO_ATUAL.md`, `configuracao.json` e `INSTALAR_NO_NOTEBOOK.md` na raiz do clone. Use o guia de instalação para reproduzir a versão atual em Windows.
2. `docs/INTEGRACAO_CODEX.md`, `docs/FLUXO_AUTOMATICO_CODEX.md`, `docs/VERIFICACAO.md`, `prompts/FLUXO_COMPLETO.md` e `prompts/manifesto_prompts.json`.
3. `scripts/interface_pesquisa.py`, `scripts/codex_apuracao.py`, `scripts/codex_rpc.py` e `scripts/fluxo_codex.py`. Veja `modelos/ACHADOS.schema.json` e `interface/revisao.js` para entender como um achado chega à tela.
4. `docs/CADASTRO_DOCUMENTOS.md`, `docs/BANCO_SQLITE.md`, `docs/ACHADOS_IA.md` e `docs/CONTINUIDADE_DOCUMENTAL.md`. Consulte `docs/VLADO_GUIA_TECNICO_DEPLOY.md` se o grupo tiver enviado o material interno junto com este briefing. O repositório contém os guias operacionais necessários para começar.

### Como rodar e verificar a versão existente

No Windows, instale Python 3.12+ com SQLite/FTS5 e o Codex CLI nativo para o modo local. O clone publicado inclui `Preparar notebook.cmd` e `Abrir mesa.vbs`. O login no ChatGPT ocorre na tela local de perguntas. O processamento do modelo é online. A disponibilidade de modelos depende da conta. Use Node.js para as regressões JavaScript da suíte. Os testes de navegador adicionais usam Playwright. As versões das bibliotecas de extração e exportação ficam em `requirements.txt`. A leitura visual opcional de PDF usa `requirements-opcional.txt`.

```powershell
git clone https://github.com/Palhunto/Vlado.git
Set-Location Vlado
git checkout --detach ff816bd81d80583fb8953a4529868ea6d3840320
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/ambiente.py
.\.venv\Scripts\python.exe scripts/montar_fluxo.py --check
.\.venv\Scripts\python.exe scripts/verificar_projeto.py
.\.venv\Scripts\python.exe -m unittest discover -s testes -v
.\.venv\Scripts\python.exe scripts/interface_pesquisa.py --porta 8765 --sem-abrir
```

A interface existente atende em `http://127.0.0.1:8765`. `APURACAO_CODEX_BIN` permite indicar o executável se a descoberta automática falhar. `APURACAO_OCULTO` é usado pelo iniciador Windows. A integração atual autentica via ChatGPT. Esses comandos e variáveis descrevem a base publicada. A configuração da versão hospedada será definida a partir das escolhas do piloto.

## 3. Comportamento atual a entender antes de decidir a arquitetura

1. **Ingestão.** `scripts/cadastrar_documentos.py` copia cada lote para o caso, registra IDs, hashes, duplicatas, falhas e recibo. `scripts/extrair_pdf.py` extrai texto por página, com indicação de páginas vazias e erros. A versão atual preserva os originais e faz extração textual sem OCR. O cadastro pode ser feito antes da pergunta.
2. **Rodada e busca.** A pergunta congela versão do corpus, manifesto, originais, derivados e instruções em `execucoes/<caso>/<rodada>/`. `scripts/nova_rodada.py` prepara o snapshot. `scripts/indice_sqlite.py` constrói o índice textual SQLite/FTS5 da rodada. `scripts/banco.py` consulta cobertura, ocorrências e contexto por IDs explícitos.
3. **Inferência.** A interface HTML/CSS/JS fala com um servidor Python local. `scripts/codex_rpc.py` inicia `codex app-server` e usa o catálogo da conta ChatGPT. `scripts/codex_apuracao.py` oferece `consultar_acervo` para cobertura, busca, leitura e entrega da etapa, além de leitura direta delimitada. `configuracao.json` tem `modelo_observado: null` na instalação inicial. Cada rodada registra o modelo reportado no momento da execução.
4. **Etapas e registros.** Os sete módulos `prompts/00` a `06` são a fonte de autoria de `FLUXO_COMPLETO.md`. `scripts/fluxo_codex.py` controla inventário, plano, busca, geração inicial, revisão e síntese. A versão atual publica `r1_busca`, `r2_revisao` e `r3_sintese` e verifica `g1` no índice separado de achados. As saídas incluem registros de consultas, mensagens, tentativas, referências, versões, `codex_fluxo_estado.json` e `codex_execucao.json`. `conversas/<id>/` preserva o histórico e o vínculo com as rodadas. Se a arquitetura mudar, preserve a rastreabilidade dessas etapas e os artefatos necessários para verificar o resultado.
5. **Conferência.** A citação resolve uma referência de caso, rodada e documento com hash e página ou linhas. O leitor mostra o trecho e abre a página física do PDF original. A revisão humana fica registrada à parte. Uma citação localizável ainda exige avaliação humana de que a passagem sustenta a afirmação.
6. **Novas levas.** Complementos mantêm a versão de corpus da conversa. Para incorporar documentos, o operador cadastra o lote, confere o recibo e adota explicitamente a versão ampliada. A próxima pergunta cria outra rodada e acrescenta uma etapa de comparação. O piloto externo pode operar com um corpus fixo durante a janela de teste. Preserve os snapshots anteriores caso o grupo publique nova versão.

## 4. Decisões delegadas à IA responsável

Escolha uma abordagem principal por tema. Registre o que será reaproveitado, o que muda, como provar que funciona e quais dependências exigem confirmação externa. Compare as opções que realmente se encaixam no projeto, considerando qualidade de evidência, tempo de implementação, operação pelo grupo, custo e facilidade de reverter. Valide disponibilidade e preços antes de assumir compromissos.

| Tema | O que decidir e entregar |
| --- | --- |
| Inferência e orquestração | Escolha provedor, modelo, forma de integração e execução das etapas. Defina como manter busca, leitura, geração inicial, revisão, síntese e publicação rastreáveis. Descreva o tratamento de falha, limite, cancelamento e repetição. Registre modelo e consumo observados em cada ensaio. |
| Interface e hospedagem | Decida quais partes da interface e do backend atuais aproveitar, quais mudanças fazer e onde executar cada componente. Defina ambiente de ensaio, hospedagem do grupo, armazenamento dos originais, índices, histórico e credenciais, além de como publicar, fazer backup, recuperar e reverter uma versão. |
| Busca e vínculo com fontes | Escolha o mecanismo de recuperação e armazenamento. Demonstre que ele encontra passagens em PDFs em português a partir de uma pergunta em inglês e que cada citação publicada resolve o mesmo original, versão, página e trecho. Defina tratamento de páginas ilegíveis e de perguntas sem suporte no acervo. |
| Acesso e ingestão | Escolha como emitir, validar e revogar convites. Assegure o acesso de cada convidado ao acervo permitido e às suas próprias consultas e resultados. Defina a rotina de cadastro e publicação de acervos pelo grupo, incluindo recibo, procedência, hashes e ativação de versões. |
| Custo e operação | Estime o custo de uma consulta completa com todas as etapas, chamadas de ferramenta faturadas, repetições e demais custos aplicáveis. Proponha cotas, concorrência, duração, retenção, teto de gasto e como o sistema aplica esse teto. Separe estimativa de medição real. O grupo confirma valores, janela, contas e responsáveis antes da execução externa. |

### Validação da qualidade

Comece com um PDF sintético cuja passagem esperada seja verificável. Teste o caminho completo da pergunta até o original e inclua uma referência de outra rodada que deve ser recusada. Depois use o acervo público, com a pergunta de demonstração, uma paráfrase em inglês e uma pergunta sem resposta nas fontes. Mantenha as respostas de referência fora dos prompts e do índice. Confira com um integrante do grupo o vínculo, o trecho, a página, a atribuição e o suporte de cada afirmação publicada. Registre as omissões, a latência e o custo real. Use essas medições para confirmar ou rever a escolha técnica.

## 5. Demonstração proposta e aceite

O acervo público proposto para o piloto reúne três fatos relevantes da Americanas S.A., de **11/01/2023, 13/06/2023 e 16/07/2024**. Os três originais e seus hashes foram conferidos na estação de origem. O clone publicado começa vazio. Peça ao grupo as cópias conferidas e registre sua procedência antes da carga. A URL direta do primeiro PDF no RI falhou na checagem anterior. O arquivo local foi conferido visualmente e o processo da CVM transcreve o comunicado. Use no leitor o PDF preservado que corresponde ao texto recuperado pela busca. [Cronologia do RI](https://ri.americanas.io/recuperacao-judicial/timeline/) · [Processo CVM 19957.003980/2023-26](https://conteudo.cvm.gov.br/export/sites/cvm/sancionadores/sancionador/anexos/2024/SEI_19957003980_2023_26.pdf)

**Pergunta sugerida**

> In its January 11, 2023 market disclosure, what preliminary amount did Americanas estimate for the accounting inconsistencies, and what was the reference date? Cite the document, page and original passage.

**Referência de aceite.** O fato relevante de **11/01/2023**, `D001_A01_fato_relevante_2023-01-11.pdf` no cadastro de origem, sustenta que **a companhia estimou preliminarmente cerca de R$ 20 bilhões na data-base de 30/09/2022**. A evidência está no primeiro parágrafo da **página física 1 de 2**, no fragmento “dimensão de R$ 20 bilhões na data-base de 30/09/2022.” O período anterior qualifica a estimativa como preliminar. SHA-256 do original conferido `9b99e2874f697a72c109a7651f30116c9b5baa52a98adafb495fb3ede91f0980`.

**Critério de aceite.** Uma pessoa de fora do grupo abre o link em um navegador limpo, entra com o convite, envia a pergunta e recebe uma resposta gerada naquele momento. Ela abre a citação, lê o trecho e chega à página 1 do PDF original sem ajuda. Registre a versão implantada, rodada, página, trecho, latência e resultado da conferência. Antes de liberar o link, verifique acesso sem convite, revogação, separação entre convidados, recarga sem duplicar consulta e acesso ao original depois de reiniciar o serviço.

## 6. Ordem de retomada e materiais

1. Abra o repositório no commit de referência, leia as instruções e confirme o comportamento da base com catálogo vazio. Registre o que reproduziu e o que só consta no histórico.
2. Entregue uma proposta técnica curta com as escolhas da seção 4, premissas, custos e sequência de trabalho. Confirme com o grupo as contas, acessos e orçamento que condicionam o ensaio hospedado. Implemente primeiro um percurso com dados sintéticos que vá da pergunta à página do original. Use esse teste para decidir quanto da implementação atual pode ser reaproveitado.
3. Carregue o acervo autorizado, ensaie com inferência real, meça qualidade e custo e valide publicação e recuperação no ambiente escolhido.
4. Execute o aceite com uma pessoa externa. Com o percurso aprovado, prepare o link e os convites para a janela acordada com o grupo.

O **clone do GitHub** contém código, prompts, testes, dependências e guias operacionais. O **grupo** entrega este briefing e, quando necessário, o guia técnico interno e os registros de QA. Para a demonstração pública, o grupo fornece os **três PDFs da Americanas**, o manifesto `fatos_relevantes_20261105_v1` e, se disponível, o recibo do lote `3e7b41b2d3424aa1b1d8bdf40fcb39df`. Mantenha os documentos de trabalho, históricos locais e credenciais fora do pacote do piloto.
