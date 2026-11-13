# Fluxo automático do Codex — 06/11/2026

Novas perguntas e complementos passam por um controlador no backend. Uma resposta do modelo encerrando seu turno já não basta para marcar a rodada como concluída: é preciso registrar as seis etapas, publicar os registros canônicos e verificar o índice separado de achados.

## Como funciona

1. A pergunta congela uma rodada e seu índice documental. Complementos preservam a thread e a versão atual do corpus da conversa, criando outra rodada. Uma ampliação exige seleção explícita em **Continuar com novos documentos**.
2. O backend conduz inventário, plano, busca, geração inicial, revisão e síntese em seis turnos internos da mesma thread. Os prompts existentes permanecem no snapshot; instruções adicionais descrevem os contratos de entrega pela ferramenta `consultar_acervo`.
3. Inventário, plano e busca recebem registros textuais. Geração inicial, revisão e síntese entregam JSON pelo campo `texto` da ação `guardar`, mantendo a ferramenta compatível com conversas existentes.
4. O backend valida as entregas e monta os campos técnicos: IDs, referências nativas, localizadores, hashes, versões e vínculos de evidência. A geração inicial publica `r1_busca`; a revisão, `r2_revisao`; a síntese, `r3_sintese`.
5. Na continuidade com novos documentos, uma sétima etapa obrigatória entrega a comparação estruturada com a última rodada concluída. Depois das etapas exigidas, o backend valida novamente os registros e os artefatos, constrói ou confere o índice de achados `g1` e só então publica a resposta final, o comparativo quando aplicável e o estado concluído.

O SQLite documental continua sendo um índice de fontes. As conclusões da IA entram no banco separado de achados; não viram documentos nem resultados do FTS documental.

## Validação e rastreabilidade

A evidência precisa corresponder a uma leitura real da rodada. A revisão exige nova leitura das fontes utilizadas. Correções criam versões com revisão explícita; evidências adicionais preservam as anteriores. A síntese só inclui a versão mais recente com suporte registrado e exige vínculos aos achados e às fontes. Sem achados sustentados, o resultado deve registrar insuficiência.

Declaração documental, alegação atribuída, inferência e pendência permanecem distintas. Ausência em busca não é prova de inexistência. Fontes continuam sendo dados de análise, sem autorização para executar instruções. Nenhum registro automático equivale a revisão independente ou aprovação humana; a execução não preenche marcações humanas automaticamente. A conferência pela interface é registrada separadamente, conforme [ACHADOS_IA.md](ACHADOS_IA.md).

Essas verificações asseguram o contrato técnico e a rastreabilidade. A avaliação semântica do suporte continua dependendo do modelo e de conferência humana.

## Correção automática, estados e cancelamento

Cada etapa tem até duas tentativas. Uma entrega inválida ou ausente retorna o motivo ao modelo para correção na mesma rodada. Candidatos rejeitados ficam preservados em arquivos novos. O prazo por turno interno é de 600 segundos; erros nativos de autenticação, conexão ou limite encerram a execução com a mensagem correspondente. Não há troca para API paga.

Falha persistente de entrega resulta em `incompleto`. A publicação final tem até duas tentativas técnicas e reutiliza registros idênticos, sem duplicar versões. Falhas não recebem resposta final verificada. Cancelamento interrompe o turno em execução e preserva saídas parciais.

A interface apresenta a etapa atual, mensagens provisórias e o estado `publicando`. O botão **Consultar achados desta rodada** abre a revisão final e a geração verificadas na área existente de achados. Atualizações anteriores à verificação continuam identificadas como provisórias, mesmo que o modelo use linguagem conclusiva.

## Arquivos e compatibilidade

- `scripts/fluxo_codex.py`: controlador das entregas, evidências, revisões e publicação.
- `scripts/codex_apuracao.py`: turnos internos, eventos, cancelamento e integração com ferramentas existentes.
- `interface/codex.js`: etapas, estados provisórios e acesso aos achados publicados.
- `saidas/codex_fluxo_estado.json`: ponteiro operacional atualizado atomicamente.
- `saidas/codex_execucao.json`: estado final, etapas validadas e recibo de publicação.
- `saidas/codex_tentativa_*.json` e artefatos identificados por hash: preservação das entregas e tentativas.

As novas rodadas registram `fluxo_automatico: 2`. As rodadas históricas R004/R005 da Americanas não foram reescritas nem publicadas retroativamente. A auditoria que encontrou etapas/publicação ausentes continua válida para aquelas execuções.

## Como usar

Inicie o servidor pelo iniciador habitual. Após uma atualização do backend, recarregue a página com Ctrl+F5. Em **Perguntar ao Codex**, escolha o caso e envie a pergunta. O restante do fluxo acontece automaticamente. Um complemento na mesma conversa também percorre todas as etapas. Para incorporar outro lote, use **Continuar com novos documentos**, confira o cadastro e escolha a versão antes de enviar. O [guia da continuidade](CONTINUIDADE_DOCUMENTAL.md) descreve comparação, conferência e preservação.

O processo Codex e o login oficial ChatGPT continuam no backend local. O modelo processa online e o uso está sujeito aos limites da assinatura. Não foi acrescentada chave de API.

## Verificações executadas

- 106 testes automatizados aprovados: registro completo (registro histórico não incluído). Incluem publicação nas duas rodadas, correção de entrega inválida, releitura na revisão, versões, evidência adicional, insuficiência, falha de índice e preservação das rodadas anteriores.
- Navegador com app-server simulado: pergunta, complemento, consulta dos achados, recarga, cancelamento, limite, separação de casos e telas de 320–1365 px; nenhum erro JavaScript. Resultado (registro histórico não incluído).
- Inferência real online, autenticada por ChatGPT, exclusivamente sobre dois textos sintéticos: R001 publicou dois achados e R002 publicou um; ambas concluíram as seis etapas, verificaram `r3_sintese/g1` e mantiveram a mesma thread. Resultado nativo (registro histórico não incluído). Isso verifica a integração, sem constituir piloto editorial ou aprovação humana.
- Verificadores de montagem/integridade e sintaxe Python/JavaScript executados.
- Serviço atualizado iniciado em `127.0.0.1:8765`, sem conversas ativas durante o reinício. Login ChatGPT Plus preservado e inventário selecionado acessível por HTTP. Conferência do serviço (registro histórico não incluído).

O teste nativo é optativo e consome acesso da assinatura:

```powershell
python testes/qa_fluxo_real.py --saida-base docs/qa_fluxo_automatico --complemento
```

## Limitações remanescentes

Não há retomada automática no meio de uma etapa após queda do backend. O histórico parcial é preservado e a recuperação registra interrupção; a próxima pergunta cria outra rodada. Achados inteiramente novos descobertos só durante a revisão não são inseridos como se já tivessem geração inicial; o fluxo aceita correções e evidências adicionais dos achados gerados e deve declarar a limitação.

OCR, adaptadores específicos para DOCX/XLSX e leitura visual de PDF sem a dependência opcional continuam fora desta alteração. A publicação automática usa evidência textual indexada ou evidência visual autorizada; leitura textual sem vínculo verificável ao índice não é promovida automaticamente a evidência canônica. Aprovações de ampliação de acesso continuam restritas pelo fluxo existente.

As seis etapas consomem vários turnos internos. Limite real de assinatura, expiração real de credenciais e recuperação após queda durante inferência não foram provocados no teste online; os caminhos de falha pertinentes foram simulados. Os resultados antigos não são migrados automaticamente.
