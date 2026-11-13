# Estado atual do projeto

Atualizado em 10/11/2026. Versão operacional e prompts: **1.3.0**. Este é o ponto único de retomada do desenvolvimento; as regras de operação ficam em [AGENTS.md](AGENTS.md).

## Operação implementada

`Interface HTML/JS → backend Python local → codex app-server → modelo online`.

- Cadastro por lote com cópias preservadas, recibos, hashes, duplicatas e extração textual de PDFs, sem OCR. Recuperação de PDFs pendentes sem reenvio.
- Corpus congelado por rodada, índice documental SQLite/FTS5, cobertura e leituras com referências verificáveis.
- Perguntas e complementos pela interface, com login ChatGPT, fontes, histórico, cancelamento e seleção de modelo pelo catálogo do runtime.
- Seis etapas controladas: inventário, plano, busca, geração inicial, revisão e síntese. Publicação e verificação do banco separado de achados antes da conclusão.
- Conferência humana por achado, com estados, observações, filtros, progresso e exportação. Marcações separadas e versionadas, sem reescrever a resposta da IA.
- Continuação com observações selecionadas explicitamente: prévia, fontes vinculadas, revalidação no envio e recibo na próxima rodada. O retorno acompanha as seis etapas para reexame.
- Continuação com novos documentos na mesma conversa: cadastro com recibo, seleção explícita da versão ampliada, outra rodada e comparação estruturada após as seis etapas. Mantém originais, respostas e conferências anteriores; os novos achados começam pendentes.
- Gerenciamento com lixeira restaurável, nomes legíveis, referências por título/página e detalhes técnicos recolhidos.
- Caderno com trechos, achados e cruzamentos humanos, origens e autores preservados; seleção explícita como contexto, com recibo na nova rodada.
- Aba **Apuração** com notas editáveis por caso, salvamento versionado, exclusão, editor Markdown com prévia, seleção de achados da IA e pesquisa documental e exportação do caderno em Markdown, PDF e DOCX editável. Fontes preservadas e conflitos entre janelas tratados sem sobrescrever o rascunho. [Uso e limites](docs/APURACAO.md).
- Diligências ligadas aos achados da IA ou do caderno: responsável, prazo, estados, histórico, respostas cadastradas/vinculadas e retomada explícita da questão, inclusive com nova versão documental.

Complementos conservam a versão atual do corpus da conversa e criam outra rodada. **Continuar com novos documentos** incorpora explicitamente uma versão ampliada; só depois do envio essa versão passa a valer nos complementos seguintes. A seleção na interface não altera o caso ativo global.

## Onde consultar

Cabeçalho corrigido em 10/11/2026: o SVG de definições do Vditor criava um espaço de 150 px antes de “Apuração atual” porque seu estilo inline era bloqueado pela CSP. A folha da aplicação agora retira esse SVG do fluxo; cabeçalho permanece sticky no topo, com ícones e CSP preservados. Regressão reproduzida e conferida em seis larguras e nos dois temas: qa_cabecalho (registro histórico não incluído).

Modo escuro aplicado em 10/11/2026: paleta grafite/sálvia aprovada no mockup, texto marfim, avisos em âmbar e ausência de suporte em coral. Botão no cabeçalho alterna claro/escuro; preferência no armazenamento do navegador, com funcionamento mesmo quando indisponível. Editor Vditor, formulários, fontes e diálogos acompanham o tema. A adaptação desktop ignora notificações repetidas do mesmo estado para preservar os controles ao redimensionar. Verificações e capturas exclusivamente sintéticas em qa_dark_mode (registro histórico não incluído).

Primeiro lote de usabilidade em 09/11/2026: reconexão do acompanhamento sem reenvio, rascunhos por apuração/conversa com destino explícito, campos estáveis nas decisões pendentes, isolamento das observações e localizadores estruturados legíveis. Abas, identidade visual, backend e dados existentes preservados. Os rascunhos vivem na página e têm aviso antes de sair; não há persistência após fechar/recarregar confirmado. Correções, testes e limites (registro histórico não incluído).

| Assunto | Fonte atual |
| --- | --- |
| Uso e início | [README.md](README.md) |
| Seleção e versão de trabalho | [configuracao.json](configuracao.json) |
| Estado do piloto de cada caso | Campo `protocolo` do manifesto do caso solicitado |
| Cadastro e extração | [CADASTRO_DOCUMENTOS.md](docs/CADASTRO_DOCUMENTOS.md) |
| Interface e gerenciamento | [INTERFACE_PESQUISA.md](docs/INTERFACE_PESQUISA.md) |
| Integração e permissões | [INTEGRACAO_CODEX.md](docs/INTEGRACAO_CODEX.md) |
| Controle e publicação | [FLUXO_AUTOMATICO_CODEX.md](docs/FLUXO_AUTOMATICO_CODEX.md) |
| Continuação com novos documentos e comparativo | [CONTINUIDADE_DOCUMENTAL.md](docs/CONTINUIDADE_DOCUMENTAL.md) |
| Contribuições humanas e cruzamentos | [CADERNO_APURACAO.md](docs/CADERNO_APURACAO.md) |
| Notas editáveis e exportações | [APURACAO.md](docs/APURACAO.md) |
| Responsáveis, respostas e acompanhamento | [DILIGENCIAS.md](docs/DILIGENCIAS.md) |
| Pesquisa nas fontes | [BANCO_SQLITE.md](docs/BANCO_SQLITE.md) |
| Registros e conferência dos achados | [ACHADOS_IA.md](docs/ACHADOS_IA.md) |
| Verificações técnicas | [VERIFICACAO.md](docs/VERIFICACAO.md) |

## Limites técnicos registrados

Sem retomada automática no meio de uma etapa após queda, OCR ou adaptadores próprios DOCX/XLSX. Leitura visual de PDF depende de PyMuPDF opcional. Achados inteiramente novos descobertos apenas na revisão ainda não entram automaticamente na publicação; correções e evidências adicionais dos achados existentes são suportadas.

A validação técnica confere contratos e rastreabilidade; o suporte semântico exige avaliação. A revisão da IA não é aprovação humana. As marcações da interface não autenticam individualmente o jornalista; só são enviadas ao modelo por seleção explícita em **Continuar com estas observações**. O contexto de uma conversa retomada conserva os retornos já enviados. Expiração real de credenciais e esgotamento real de cota não foram provocados nos testes registrados.

## Manutenção

Usar os iniciadores existentes para abrir a Mesa. Antes de reiniciar o backend, conferir ausência de execução ativa. Não presumir login, modelo ou estado do serviço a partir de registros antigos.

Após alterações pertinentes, executar os três comandos de verificação de AGENTS.md. Manter resultados de testes separados dos documentos da apuração. Preservar originais, snapshots, saídas brutas, registros de revisão, procedência e referência original.

Esta cópia de migração começa com catálogo vazio e seleção global vazia.
