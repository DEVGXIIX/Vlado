# Codex na Mesa de apuração

Perguntas e complementos têm seis etapas obrigatórias e publicação automática verificada no banco de achados. Veja o [fluxo automático e suas limitações](FLUXO_AUTOMATICO_CODEX.md) e a [verificação técnica atual](VERIFICACAO.md).

## Diagnóstico e escolha

A interface ativa é HTML/CSS/JavaScript, servida por `scripts/interface_pesquisa.py` com `ThreadingHTTPServer`, somente em `127.0.0.1`. O navegador chama endpoints JSON com token de sessão local, validação de Host e Origin. O backend usa as funções de `indice_sqlite.py` e `indice_achados.py`; não há servidor de inferência ou banco vetorial. O SQLite documental é aberto para leitura e cada consulta/contexto gera um registro novo na rodada. O banco separado de achados continua tendo contratos próprios de publicação e revisão.

Um adaptador Python controla `codex app-server --listen stdio://`. O backend traduz as ferramentas da conversa para as mesmas funções validadas, sem construir comandos shell a partir da pergunta ou de documentos. O protocolo usa `initialize`, `thread/start`, `thread/resume`, `turn/start`, notificações de mensagens/ferramentas e `turn/interrupt`. O navegador acompanha eventos por POST com cursor e espera de até 20 segundos; novos eventos liberam a resposta imediatamente. Não é necessário expor WebSocket ou porta do Codex ao navegador.

O executável observado nos testes de integração foi `codex-cli 0.144.6`. A inferência autenticada foi exercitada com corpus sintético, incluindo pergunta, complemento e publicação dos achados. O modelo é selecionado pelo catálogo do runtime; cada execução registra o nome efetivamente informado pelo servidor.

O [app-server oficial](https://developers.openai.com/codex/app-server) atende ao ciclo de vida interativo, com histórico, interrupção e solicitações do servidor. `codex exec --json` é útil para tarefas delimitadas, mas exigiria reconstruir mais desse ciclo na aplicação. O [SDK oficial](https://developers.openai.com/codex/sdk) também é uma opção de integração local; não é correto presumir que exija chave de API. O transporte direto foi escolhido para usar o executável já instalado e não adicionar SDK/Node ao backend. A documentação atual pode descrever campos posteriores à versão instalada; o contrato implementado foi conferido nos schemas locais.

## Iniciar e usar

1. Se havia um servidor anterior aberto, encerre-o primeiro para carregar os scripts novos.
2. Abra **Abrir mesa.vbs** nesta pasta. Ele inicia o servidor oculto e abre o navegador. Se o Windows bloquear Windows Script Host, use **Iniciar pesquisa.cmd**. A alternativa é `python scripts/interface_pesquisa.py`. O acesso padrão é `http://127.0.0.1:8765`.
3. Cadastre os arquivos na área existente e confira o recibo, duplicatas, hashes e limitações de extração. Somente o envio da pergunta inicia uma rodada.
4. Abra **Perguntar ao Codex**. **Verificar conexão** consulta a versão e o tipo de login. **Entrar com ChatGPT** solicita `account/login/start` com `type=chatgpt`; o backend tenta abrir a URL oficial no navegador. Se nenhuma janela aparecer, clique em **Abrir página de login**, que abre o mesmo fluxo em uma nova aba. Complete o login e volte à mesa. A tela acompanha a conclusão. **Cancelar login** cancela o fluxo pendente. Erros de início aparecem junto ao botão.
5. Escolha o caso e confira o inventário. Nesta primeira entrega o conjunto é o **caso completo**, sem seleção de subconjunto por documento.
6. Digite a pergunta e envie. A interface mostra preparação, execução, mensagens parciais, ferramentas, fontes consultadas e estado final. O painel de andamento mantém erros e avisos.
7. Marcadores `[fonte:SHA256]` válidos levam às fontes lidas, com caso, rodada, documento, página física/linhas ou localizador disponível, trecho e hash. **Baixar original preservado** valida o snapshot e o hash antes do download. Referências sem leitura registrada permanecem explicitamente pendentes.
8. Envie um complemento na mesma conversa. Ela retém sua thread, mas cada pergunta recebe nova rodada, índice e registros. Complementos usam a versão de corpus atual da conversa. Cadastros novos não entram silenciosamente: use **Continuar com novos documentos**, confira o recibo e selecione a versão ampliada para a próxima pergunta. Essa rodada inclui comparação com a última resposta concluída. [Guia](CONTINUIDADE_DOCUMENTAL.md).
9. **Cancelar execução** envia `turn/interrupt`; a interrupção é confirmada pelo evento final. A preparação também pode ser cancelada; uma operação de cópia/indexação já iniciada termina antes de liberar a preparação. As saídas parciais são preservadas.
10. Recarregue a tela, escolha o caso e a conversa para recuperar o histórico. Fechar somente o navegador não para o trabalho. **Encerrar serviço** encerra o backend e seu processo Codex, interrompendo os trabalhos ativos. Não faz logout da conta do Codex.

O caminho do executável é encontrado no PATH ou na instalação do aplicativo Codex sob `LOCALAPPDATA`. Para outra instalação, defina **APURACAO_CODEX_BIN** no ambiente do backend, apontando para um executável nativo. Não se aceita `.cmd`, `.bat` ou `.ps1` como binário Codex. O iniciador reaproveita a localização de Python já existente no projeto.

## Autenticação e permissões

A [autenticação oficial](https://developers.openai.com/codex/auth) distingue acesso pela assinatura ChatGPT e cobrança de API. A integração exige conta do tipo `chatgpt`, configura `forced_login_method=chatgpt` e remove variáveis de chave de API do ambiente do filho. Ela não implementa fallback para cobrança por chave. A disponibilidade e os limites continuam sujeitos à conta/workspace; login bem-sucedido não garante acesso irrestrito a modelos ou cota.

O próprio runtime oficial armazena e renova credenciais. O projeto não abre arquivos de autenticação, não copia tokens e não envia credenciais da conta ao frontend. A URL de login é aberta no backend e não é gravada nos eventos. O token de sessão do servidor HTTP é apenas proteção local contra requisições indevidas, distinto da autenticação ChatGPT. Stderr do filho não é publicado, e mensagens de erro passam por redução/remoção de padrões de credenciais. Não habilitar logs brutos do protocolo com autenticação.

A alternativa **Abrir página de login** usa um redirecionamento local, protegido pelo cookie HttpOnly/SameSite da sessão. A URL oficial permanece em memória no backend enquanto há login pendente; não é devolvida em JSON nem persistida no histórico. Somente URLs HTTPS dos hosts oficiais `auth.openai.com` e `chatgpt.com` são aceitas. Falha da abertura automática não impede o uso do link.

O servidor usa porta exclusiva no Windows para impedir que várias instâncias atendam endereços iguais com versões diferentes. Se um servidor antigo ainda servir arquivos novos, a área de conversa identifica a incompatibilidade e orienta a reinicialização. Depois de reiniciar o backend, recarregue a página para renovar a sessão.

O processo filho desativa busca web, apps, plugins, hooks não gerenciados, memória, shell, agentes auxiliares e ferramentas de navegador/computador por configuração. Servidores MCP herdados são desativados nas configurações da thread. Um [perfil de permissões](https://learn.chatgpt.com/docs/permissions) temporário `apuracao_acervo` nega a raiz, permite apenas os caminhos mínimos do runtime e leitura de um workspace vazio da conversa, sem rede para ferramentas locais. O acervo é disponibilizado pelas ferramentas do backend com autorização de caso/rodada e hashes. Não há escrita direta do modelo nos documentos. As permissões e configurações administradas continuam sendo verificadas pelo Codex; incompatibilidades falham sem fallback para acesso amplo. O backend exige confirmação do perfil ativo e da política de leitura/sem rede antes de enviar a pergunta.

`approvalPolicy=on-request` é mantida. Solicitações de comando, alteração de arquivo, permissão e perguntas ao usuário aparecem na tela. Esta primeira versão permite responder às perguntas e **recusar** ampliações de escrita/rede ou comandos. Para conceder acessos mais amplos seria necessário outro fluxo revisado; cancelar permanece disponível. Solicitações desconhecidas recebem recusa explícita e aviso, sem aprovação automática. Não se altera configuração de permissões ou credenciais de outras sessões.

As regras técnicas de ferramentas e os prompts reduzem o risco de mistura/instruções documentais; não constituem garantia universal contra injeção de prompt ou contra processos externos no computador. O modelo continua online, independentemente de a rede de ferramentas estar desabilitada.

## Recuperação do acompanhamento e rascunhos

Se a leitura dos eventos falhar, **Reconectar acompanhamento** volta a observar a mesma conversa a partir do cursor já recebido, sem reenviar a pergunta, criar rodada ou reiniciar a execução. **Cancelar execução** permanece disponível. Durante a reconexão, o envio de perguntas fica bloqueado até a interface recuperar o estado do backend. Isso recupera o acompanhamento HTTP; não retoma automaticamente uma etapa interrompida por queda do backend.

O campo de pergunta mantém rascunhos separados para cada par apuração/conversa, incluindo uma entrada própria para **Nova conversa** em cada apuração. O destino aparece junto ao campo. Trocar de área ou contexto não descarta esses textos; um envio confirmado limpa apenas o rascunho enviado, e uma falha de envio preserva o texto. Prévia de observações, caderno ou diligências recupera o rascunho do destino antes de sugerir uma pergunta.

Os rascunhos ficam somente na memória da página, sem escrita no corpus, nos registros ou no armazenamento persistente do navegador. Ao fechar ou recarregar com texto pendente, a interface solicita a confirmação nativa do navegador. Confirmar a saída descarta os rascunhos; eles não são recuperados após fechar a página ou cair o navegador. Esta proteção depende das condições do navegador para `beforeunload`.

Pedidos de decisão são atualizados por identificador; enquanto o pedido e a pergunta permanecerem ativos, seus campos não são substituídos. Texto, seleção e foco permanecem durante as atualizações. Um envio em andamento ou já aceito não é reabilitado pelo próximo lote de eventos; falhas de resposta permitem tentar novamente. A política de recusar ampliações de acesso permanece igual.

## Corpus, prompts e registros

`nova_rodada.py` passou a aceitar um caso explícito por função. Isso congela a configuração selecionada sem alterar `configuracao.json` global nem ler o corpus ativo de outro caso. Os pontos antigos de chamada continuam funcionando. O snapshot inclui as instruções, módulos/manifesto de prompts, fluxo completo, configuração, documentos/derivados/recibos e README disponível. Os prompts editoriais originais não foram reescritos.

Uma adaptação de transporte é acrescentada às instruções da thread: o backend já fez cadastro/congelamento; a ferramenta `consultar_acervo` substitui os comandos dos scripts, sem substituir suas validações. Ela oferece cobertura, busca, contexto, leitura textual delimitada, imagem/página de PDF e salvamento de etapas. Conteúdo de fontes chega como resultado de ferramenta, tratado expressamente como dado não confiável. Só se aceitam IDs documentais do manifesto congelado; não se aceitam caminhos ou SQL fornecidos pelo modelo. Leitura visual de PDF exige PyMuPDF opcional, ausente no ambiente observado; sem ele a ferramenta informa a limitação e remete ao original. A leitura textual de PDFs continua usando os derivados existentes, sem OCR.

Os estágios inventário, plano, busca, geração inicial, revisão e síntese têm arquivos novos e identificados por hash. O backend conduz cada etapa em turno interno, valida sua entrega e tenta corrigir uma falha antes de declarar a execução incompleta. A geração inicial precede revisão e síntese, e a publicação canônica e seu índice precisam ser verificados antes do estado concluído. Toda mensagem concluída é preservada separadamente; mensagens do modelo anteriores à publicação são provisórias. Término do turno não é aprovação editorial. Não se valida automaticamente a compatibilidade semântica entre uma afirmação e seu trecho.

A identidade de passagem do índice existente é estável entre rodadas. Por isso o adaptador fornece ao modelo uma `referencia` que inclui caso/rodada e preserva a identidade nativa em `referencia_sqlite`. Um complemento precisa buscar e ler a passagem na sua própria rodada antes de citá-la. Isso impede que uma fonte da pergunta inicial seja apresentada silenciosamente como leitura da rodada seguinte. Os logs SQL originais continuam com a identidade nativa; os registros da ferramenta preservam as duas identidades.

- `conversas/<id>/conversa.json`: vínculo ao caso/corpus, thread, rodadas, modelo e estado; ponteiro operacional atualizado atomicamente.
- `conversas/<id>/eventos.jsonl`: histórico anexado de perguntas, atualizações e fontes, sem tokens.
- `execucoes/<caso>/<rodada>/saidas/consultas_sqlite/`: logs do núcleo existente.
- `saidas/codex_ferramenta_*.json`: argumentos/resultado efetivos, sem base64 das imagens.
- `saidas/codex_mensagem_*.md`: mensagens brutas concluídas, sem sobrescrever.
- `saidas/codex_<etapa>_<id>.md`: etapas preservadas, incluindo versões novas.
- `saidas/codex_execucao.json`: estado final, fontes lidas, etapas faltantes e condições da revisão.

Uma queda preserva os eventos e marca a execução como interrompida/erro ao recuperar. Retomar faz `thread/resume` da thread vinculada; não usa threads de outros casos. Complementos retêm o contexto anterior e isso é registrado como limitação experimental. Não se declara aprovação humana nem geração experimental limpa. O uso simultâneo de dois backends sobre a mesma pasta não é suportado para editar a mesma conversa; use uma única instância do servidor.

## Verificação e pendências

A suíte usa casos temporários sintéticos. Foram testados: fluxo de ferramenta pelo protocolo simulado, SQLite real, leitura/contexto, referências/download, preservação de originais e índice, snapshots de complementos após novo cadastro, separação de casos, execução concorrente na mesma conversa recusada, ordem dos artefatos, falha de login, perda de conexão, histórico persistente e recusas de permissão.

O teste de navegador `testes/qa_codex.py` usa Playwright e app-server simulado. Confere pergunta, andamento, fonte clicável, download, HTML inerte, complemento, recarga/histórico, cancelamento, erro de limite, seleção de outro caso e layout entre 320 e 1365 px. Os registros ficam em `docs/qa_codex/`. O Chromium headless empacotado falhou por dados ICU indisponíveis; o teste foi concluído com o Chrome instalado, em perfil temporário isolado.

Um smoke separado iniciou o servidor real sem abrir navegador, consultou `codex-status` por HTTP usando o executável instalado e encerrou o serviço pelo endpoint protegido. Todos responderam com sucesso; nenhuma inferência foi solicitada. O teste de inicialização do Windows Script Host recebeu acesso negado ao carregar configurações neste ambiente, portanto a execução do iniciador VBS não foi validada. Use o iniciador CMD se o sistema bloquear VBS. Os resultados observados estão em `docs/qa_codex/smoke_real.json`.

Comandos principais:

```powershell
python scripts/montar_fluxo.py --check
python scripts/verificar_projeto.py
python -m unittest discover -s testes -v
node --check interface/app.js
node --check interface/codex.js
```

Para repetir a verificação de navegador, fornecer o diretório de módulos Node contendo Playwright e, se necessário, `--chrome CAMINHO_CHROME`:

```powershell
python testes/qa_codex.py --modulos-node CAMINHO_MODULOS --saida docs/qa_codex --chrome CAMINHO_CHROME
```

**Atualização dos testes:** o login ChatGPT existente foi utilizado com sucesso em inferência online sobre corpus sintético. Pergunta e complemento publicaram achados verificados na mesma thread. Se outra instalação não estiver autenticada, use **Entrar com ChatGPT**. Expiração real de credencial e limite real de assinatura não foram provocados. O fluxo de limite foi simulado; a UI exibe o erro recebido, não tenta contornar limites nem troca para API paga.

Outros limites: ferramentas dinâmicas usam API experimental; atualização do CLI pode exigir ajuste de protocolo; não há retomada automática de uma etapa após queda do backend; não há OCR nem leitura visual de PDF sem a dependência opcional; DOCX/XLSX continuam sem adaptador próprio neste fluxo; a seleção inicial cobre o caso inteiro; não há aprovação de ampliação de acesso. Esses pontos não são apresentados como capacidades testadas.
