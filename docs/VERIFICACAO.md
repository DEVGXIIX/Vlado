# Verificação do VLADO

## 1.4.0 — integração por API e piloto hospedado (13/11/2026)

- **Testes automatizados:** 252 testes Python e 15 testes JavaScript na estação de desenvolvimento (Windows, Python 3.11). Falhas restantes: um teste de continuidade intermitente por tempo de execução (já existente antes) e, na suíte longa, os testes de exportação que rodaram antes da instalação do `python-docx` (passam depois de instalado). O teste do iniciador `.cmd` só roda com `VLADO_TESTAR_INICIADOR=1`, porque abre uma janela de console.
- **Ensaio real pela API** (`testes/qa_fluxo_real.py`, corpus sintético de dois textos fictícios, uma pergunta, sem complemento):
  - provedor OpenAI, modelo informado `gpt-6.1-sol`, chave colada na Mesa;
  - 6 etapas concluídas, publicação `r3_sintese/g1` verificada com 2 achados, nenhuma referência pendente;
  - 21 chamadas à API, 388.175 tokens de entrada (357.466 em cache) e 4.877 de saída, em 1 min 41 s;
  - custo estimado pelo preço de tabela: cerca de US$ 0,18 (confirmar no painel do provedor);
  - a resposta citou cada documento na linha correta e declarou os limites; não houve conferência humana.
- **Tentativa anterior:** parou na síntese com "Acesso negado" ao gravar `conversa.json` (duas gravações simultâneas no Windows), depois de cerca de US$ 0,16 em tokens. Corrigido no commit `c91912f`.
- **Não verificado:** pergunta em inglês sobre PDF em português, os PDFs da Americanas, o provedor Anthropic com chave real, a imagem Docker e a implantação num servidor.

## Registro anterior (1.3.0)

O verificador de projeto confere a integridade dos prompts e o estado inicial do catálogo. Os testes automatizados usam dados sintéticos e um runtime simulado. Veja os comandos em [README.md](../README.md) e o diagnóstico em [INSTALAR_NO_NOTEBOOK.md](../INSTALAR_NO_NOTEBOOK.md).

A cópia de migração de 13/11/2026 passou na integridade inicial, em 165 testes automatizados e na abertura HTTP com catálogo vazio, sem iniciar o modelo. O ensaio usou o Python disponível na estação de preparação. Instalação e login na estação de destino precisam ser verificados após a transferência.
