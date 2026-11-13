# Acompanhar diligências

Uma diligência transforma uma pendência em ação acompanhável, mantendo o vínculo com o achado que a originou. O registro contém ação, responsável declarado, prazo opcional, estado e histórico com autor, data e justificativa. Os nomes são informados pelo usuário, sem autenticação individual.

## Criar e assumir

Abra um achado em **Achados da IA**, inclusive pela referência do briefing, e escolha **Criar diligência**. A identidade preserva caso, rodada, revisão, hash, ID e versão do achado. Registros do **Caderno da apuração** também podem originar diligências, preservando sua autoria humana.

Descreva a ação e o responsável. Ela começa **A solicitar**. Em **Diligências**, use **Assumir / atualizar** para mudar o responsável, prazo ou estado e registrar uma justificativa. Estados disponíveis:

| Estado | Uso |
| --- | --- |
| A solicitar | Ação cadastrada, ainda a encaminhar. |
| Em andamento | Trabalho assumido e em execução. |
| Aguardando resposta | Solicitação encaminhada pelo jornalista. |
| Resposta recebida | Retorno disponível para conferir. |
| Concluída | Encerramento declarado pelo jornalista, com justificativa. |
| Cancelada | Ação interrompida por decisão humana, com justificativa. |

A Mesa registra o acompanhamento. Solicitações a assessorias, pedidos de LAI e outros contatos continuam a cargo do jornalista; nenhum e-mail ou mensagem é enviado por esses botões. Filtros permitem consultar estado, responsável e texto da pendência/ação.

## Receber e anexar uma resposta

1. Clique em **Anexar resposta** na diligência.
2. Cadastre os arquivos recebidos e confira o recibo de todos, inclusive duplicatas e limitações da extração PDF. Eles entram no mesmo caso antes de qualquer análise. Também é possível escolher documentos já cadastrados.
3. Selecione os documentos que compõem a resposta, identifique quem registra o recebimento e descreva o que deve ser reexaminado.
4. Clique em **Vincular resposta recebida**. O histórico conserva os documentos, hashes, versão e autoria do registro; os originais podem ser baixados.

O vínculo marca **Resposta recebida**. Não conclui a diligência, não modifica o achado de origem nem concede aprovação humana à IA. Se o vínculo falhar após o cadastro, os documentos continuam preservados; atualize a lista antes de reenviar. Arquivos recusados ou inacessíveis permanecem pendentes, sem recibo de recebimento completo.

## Retomar a questão

Escolha a conversa de destino e clique em **Retomar esta questão**. Para uma conversa com corpus anterior à resposta, marque **Incorporar os documentos novos na conversa selecionada**. A prévia da pergunta mostra a diligência e a versão documental proposta; é possível retirar a seleção antes de enviar.

Enviar cria outra rodada. As diligências selecionadas acompanham todas as etapas, com instrução de reabrir os originais, atribuir declarações às fontes e explicar o que ficou esclarecido ou continua pendente. Se houve ampliação do corpus, ocorre também o comparativo da [continuidade documental](CONTINUIDADE_DOCUMENTAL.md). A IA não altera estados das diligências; o jornalista decide o encerramento.

Fontes ausentes da versão escolhida bloqueiam o envio até incorporar os documentos ou escolher uma nova conversa. Mudanças no registro depois da prévia exigem nova seleção. A seleção vale para aquela pergunta; contexto humano anterior pode continuar no histórico da conversa.

## Arquivos preservados

Eventos ficam em `casos/<id>/diligencias/<id>/`, em arquivos novos ligados pelo hash anterior. Cada atualização confere a versão que o usuário abriu, recusando sobrescrita por outra janela. Respostas mantêm a versão do manifesto em que foram vinculadas. A seleção enviada fica congelada em `saidas/diligencias_recebidas.json`, com hash no relatório da nova rodada e exibição no histórico da conversa.

Diligências não entram no FTS como documentos, não substituem evidências e não reescrevem snapshots ou saídas antigas. Histórico com hashes não constitui assinatura digital nem autenticação de identidade.
