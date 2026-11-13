# Calibração e avaliação

Este documento descreve o método sem fornecer gabaritos ou respostas esperadas de perguntas específicas. Nenhum teste principal está autorizado na configuração inicial.

## Preparação

Abrir um novo chat do projeto e usar `COMECAR_AQUI.md`. Sem caso ativo, aguardar os documentos ou a escolha explícita de um caso. Depois verificar o comportamento de espera: encontrar documentos deve produzir inventário, não uma investigação espontânea. Registrar as ferramentas e o nome do modelo realmente disponíveis.

Verificar também o [cadastro anterior à pergunta](CADASTRO_DOCUMENTOS.md): enviar documentos em mais de um lote, conferir que cada item aparece no recibo e no inventário acumulado, que duplicatas são identificadas e que falhas não são tratadas como recebimento completo. O cadastro deve ser persistido sem rodada, índice ou geração. Ao enviar a pergunta, conferir o snapshot de todos os documentos/recibos antes de avaliar o restante do fluxo. Esse procedimento ainda precisa de observação no uso do assistente; testes técnicos não comprovam que o modelo seguirá a instrução.

O avaliador escolhe, fora do alcance da geração, passagens de referência nos originais. Faz perguntas específicas de calibração sem anexar o gabarito e depois confere fonte, sentido, números, atribuições e localizadores. Pode incluir uma pergunta sem resposta, sem informar previamente ao gerador qual é essa pergunta.

## O que observar

| Dimensão | Registro humano necessário |
| --- | --- |
| Recuperação | A passagem necessária foi localizada? O que ficou sem cobertura? |
| Suporte | A redação exata está sustentada pelo original? |
| Atribuição | Declaração de fonte foi distinguida de evento comprovado? |
| Cruzamento | Identidade, data, moeda, unidade e natureza dos campos são compatíveis? |
| Referências | Documento e localizador existem e permitem retornar à origem? |
| Insuficiência | O assistente reconhece limites sem preencher por memória? |
| Revisão | Tempo e correções humanas necessários; contar apenas o que foi observado |
| Condução | Espera, mudança de corpus, versionamento e preservação da primeira saída |

Começar com leitura e localização em um documento; depois testar cruzamento de duas peças. Ajustar prompts ou derivados apenas com motivo registrado. Repetir a calibração necessária antes de fixar uma versão.

## Passagem para o teste principal

Exige decisão explícita do operador de que o piloto daquele caso foi estabilizado, corpus e perguntas fixados e condições registradas. Só então atualizar `piloto_estabilizado` e `teste_principal_autorizado` no campo `protocolo` do manifesto desse caso. Não usar alteração dos campos para esconder uma calibração que falhou; a aprovação não é herdada por outra pauta.

Perguntas principais usam novas sessões comparáveis e snapshots próprios, sem resultados anteriores ou revisões humanas no contexto. O estado inicial deste pacote é preparação para piloto; testes automatizados de arquivos não mudam esse estado.

Um acervo público conhecido pode já constar do treinamento do modelo. Este desenho observa disciplina no uso de fontes fornecidas, sem demonstrar descoberta inédita ou eliminação de conhecimento prévio.
