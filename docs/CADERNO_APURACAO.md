# Caderno da apuração

Para notas com edição/exclusão, Markdown e exportação em PDF/DOCX, use a nova [aba Apuração](APURACAO.md). Este guia descreve o caderno anterior de contribuições imutáveis, preservado para cruzamentos, perguntas e diligências.

O caderno guarda contribuições humanas separadas dos achados produzidos pela IA. Cada registro identifica apuração, versão documental, documento e hash, localização observada, trecho, anotação, data e autor declarado. Esta versão não autentica individualmente o autor.

## Registrar uma passagem

1. Abra **Caderno da apuração**, selecione a apuração e escolha **Adicionar ao caderno da apuração**. Também há esse botão junto às fontes da pesquisa, dos achados e da conversa: selecionar texto dentro da passagem preenche somente essa seleção.
2. Confira o original. Em PDF, informe a página física do arquivo; em outros formatos, informe linhas, células ou outra localização observável.
3. Escolha trecho ou achado, dê um título e identifique a autoria. Achados exigem anotação humana.
4. Salve. O cadastro do caderno não cria rodada, índice ou chamada ao modelo.

O extrator procura o trecho na página do PDF ou no arquivo textual. Se não o localizar, o formulário exige a declaração explícita de transcrição manual após conferir o original. O registro conserva essa limitação. Localizar literalmente um trecho não valida sua interpretação. Os originais permanecem disponíveis para download.

## Cruzar e perguntar

Selecione de dois a vinte registros e use **Criar cruzamento humano**. Escreva a relação e identifique seu autor; os registros e as autorias anteriores continuam vinculados. A exportação JSON inclui somente a seleção explícita, com suas fontes.

Para levar de um a vinte registros a uma pergunta, selecione o destino e clique em **Usar selecionados numa pergunta**. A prévia pode ser retirada; apenas enviar a pergunta inicia a análise. O backend revalida IDs, hashes e fontes e salva `saidas/caderno_recebido.json` na nova rodada. As contribuições acompanham cada etapa, como contexto humano para reexame, sem aprovação automática ou inclusão no índice documental.

Fontes ausentes do corpus da conversa exigem **Continuar com novos documentos**, ou uma nova conversa sobre os documentos cadastrados. Os próximos complementos não recebem novamente os registros por seleção automática; a conversa pode conservar o contexto anterior, indicado nos metadados.

## Preservação

Registros novos ficam em `casos/<id>/caderno/registros/`; suas origens documentais ficam em `caderno/origens/`. Os registros desta área são imutáveis. Reenviar a mesma tentativa não duplica a contribuição; outra tentativa com conteúdo diferente exige novo registro. Falhas de integridade não são apresentadas como caderno vazio. A edição e exclusão individual de notas são oferecidas separadamente na aba Apuração.

Cada contribuição pode originar uma [diligência](DILIGENCIAS.md). O acompanhamento conserva a distinção entre autoria humana e resultado da IA.
