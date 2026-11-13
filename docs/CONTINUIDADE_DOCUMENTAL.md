# Continuar com novos documentos

Na conversa concluída, use **Continuar com novos documentos**. A função mantém a thread e permite incorporar arquivos à apuração sem fragmentar seu histórico.

## Cadastro e escolha da versão

1. Selecione os documentos e clique em **Cadastrar documentos**. Cada lote é registrado imediatamente, com cópias preservadas, IDs, hashes, duplicatas e resultado da extração de PDFs. O cadastro não cria rodada nem inicia análise.
2. Confira o recibo e a prévia de todos os documentos novos em relação à última análise concluída. Para usar lotes já cadastrados neste caso, clique em **Conferir documentos já cadastrados**.
3. Clique em **Usar esta versão na próxima pergunta**, ajuste a pergunta e envie.

A nova rodada congela o corpus ampliado, com índice próprio, usando a mesma conversa. Os originais da rodada anterior precisam permanecer com os mesmos IDs, caminhos e hashes; a operação é de acréscimo. Complementos seguintes conservam essa nova versão. Outros cadastros não são incorporados automaticamente. A seleção global do caso não muda.

Duplicatas entram no recibo, mas não criam uma versão documental nova por si. Falha de cadastro não é tratada como recebimento completo. Limitações de extração ficam visíveis; não há OCR. Os limites existentes continuam sendo 50 MB por envio e o máximo de documentos configurado no projeto.

Se o cadastro ou a conversa mudar depois da prévia, o envio é recusado até nova conferência. Retirar a versão da pergunta preserva o cadastro e mantém a versão atual da conversa. Execuções ativas impedem o cadastro pela ação de continuidade. A função exige uma rodada concluída com publicação verificável para servir de referência.

## Comparativo

Após inventário, plano, busca, geração inicial, revisão e síntese, a etapa adicional `comparacao` relaciona os achados da última resposta concluída aos da rodada atual. A entrega precisa cobrir todos os achados dos dois lados, sem repetir IDs; grupos permitem fusões e desdobramentos.

As classificações são mantida, alterada, pendência respondida, nova e não retomada. A classificação é uma avaliação atribuída à IA. IDs anteriores conservam caso, rodada e versão; não se tornam evidências da rodada atual. Uma pendência só pode ser classificada como respondida se o achado anterior era pendência e a conclusão atual estiver sustentada e incluída, com suporte de documento novo. Essa validação técnica não certifica que a interpretação ou a correspondência semântica estejam corretas.

A devolutiva destaca:

- **Evidências novas:** registros de fontes dos documentos incorporados, com trecho, localizador, acesso à leitura da rodada e download do original.
- **Conclusões alteradas:** redações anteriores e atuais, com justificativa da IA e acesso ao achado atual.
- **Pendências respondidas:** vínculos entre a pendência anterior e o achado atual com suporte novo.
- **Achados para nova conferência:** novos, alterados ou com evidências de documentos novos. Todos os achados da nova rodada começam pendentes; avaliações humanas anteriores não são herdadas.

Achados mantidos, novos e não retomados também ficam disponíveis. Não retomado não significa refutado. Documentos novos sem leitura registrada são destacados como lacuna; o comparativo não cobre seu conteúdo. Uma resposta de assessoria permanece declaração atribuída, sem conversão automática em verdade externa.

## Registros e preservação

`saidas/continuidade_entrada.json` conserva a seleção da versão, origem/destino, documentos novos e achados anteriores fornecidos como contexto. O relatório de execução aponta seu hash. A entrega bruta da comparação é preservada entre as tentativas; o comparativo validado fica em `saidas/codex_comparativo_<hash>.json`, com hash no relatório final. A interface permite exportá-lo e recuperá-lo no histórico após recarga.

O comparativo não é inserido no FTS documental nem modifica os registros canônicos anteriores. Os achados atuais continuam usando suas próprias leituras e revisões. Falha persistente da comparação resulta em rodada incompleta, com saídas parciais preservadas, sem sucesso final verificado.

Resultados anteriores são fornecidos explicitamente como contexto para comparar; isso é registrado e não constitui geração experimental limpa. Observações humanas podem acompanhar a pergunta mediante a seleção explícita já existente. O comparativo é produzido pela mesma IA, sem revisão independente ou aprovação humana automática.
