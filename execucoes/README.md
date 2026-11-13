# Registros de execução

Inicialmente não há rodadas de apuração. Testes de infraestrutura usam pastas temporárias e não são resultados editoriais.

Depois de selecionar um caso e receber a pergunta, criar uma rodada com `scripts/nova_rodada.py`. A pasta contém pergunta original, registro de condições, manifesto de hashes e cópia congelada de documentos, derivados e prompts. Guardar saídas em `saidas`:

```text
<caso_id>/R001/
  00_pergunta_original.md
  registro.json
  snapshot.json
  entradas/
  indice/v1/
    apuracao.sqlite              # derivado das entradas congeladas
    manifesto.json              # procedência, cobertura e hash do banco
  saidas/
    consultas_sqlite/            # retornos brutos em JSON, um arquivo por execução
    01_inventario.md
    02_plano.md
    03_buscas.md
    04_evidencias_brutas.md
    05_cruzamentos_brutos.md
    06_revisao_assistida.md
    07_achados_revisados.md
    08_briefing.md
    09_retorno_humano.md          # apenas quando existir retorno real
    10_briefing_revisado_v2.md    # apenas quando produzido
```

Os arquivos de saída não são criados preenchidos pelo script. O agente deve gravá-los durante as etapas, antes de corrigir sua geração. São artefatos produzidos pelo agente, não captura automática integral do chat. O operador pode exportar ou guardar a conversa completa para auditoria. Casos diferentes podem ter uma R001 cada; a referência completa sempre inclui o caso. Trocar de caso nunca reutiliza os achados ou a aprovação do piloto de outro.

Não sobrescrever saídas iniciais. Rodadas diferentes usam IDs novos; perguntas principais usam sessões novas comparáveis e somente as entradas previstas. Não consultar outra rodada para completar a resposta.

Na versão 1.1.0, o índice é criado na preparação da rodada quando habilitado. Saídas editoriais continuam a cargo do agente; JSONs de consulta são gravados automaticamente pela ferramenta quando executada. O índice e seu manifesto ficam fora do `snapshot.json`. Novas gerações usam nomes próprios (`v2` etc.) e preservam as anteriores. Ver [guia SQLite](../docs/BANCO_SQLITE.md).

O snapshot congela arquivos, mas não congela pesos do modelo, comportamento do serviço ou ferramentas da conta. Não chamar uma pasta separada de sandbox de segurança. Se o agente já conheceu gabaritos ou avaliações, registrar a condição.
