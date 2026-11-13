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
- **Apagamento definitivo, retomada, caderno com autoria pela conta e teste ponta a ponta** (commits `06ee326` e `0a0d6ce`): suíte completa com 324 testes Python 3.12, todos OK (1 pulado: o iniciador `.cmd`). O teste ponta a ponta (`testes/test_ponta_a_ponta.py`) restaura um backup em outra instalação e confere, pelo HTTP do piloto, originais com o mesmo hash, caderno com autoria, original aberto na página citada, histórico e isolamento entre duas contas. Nenhuma chamada de modelo.
- **Imagem Docker** (`docker build`, Docker 29.9.3 no Windows, imagem de 238 MB comprimida):
  - Python 3.12.16, OCRmyPDF 16.10.4, PyMuPDF 1.28.2, Tesseract 5.3.0 com `por`, `eng` e `osd`, Ghostscript 10.00.0, pngquant 2.17.0, unpaper 7.0.0;
  - OCR real de um PDF só-imagem dentro do container pelo motor `ocrmypdf`, com o texto reconhecido sem erro;
  - processo como usuário `vlado` (uid 10001), código sem permissão de escrita, pastas de dados graváveis; a imagem não contém chaves, ajustes, convites, casos, testes, `.venv` nem `.git`;
  - `HEALTHCHECK` chega a `healthy`, `/saude` responde `{"ok": true}` e a página sem convite responde 401; `docker compose config` válido.
- **Não verificado:** pergunta em inglês sobre PDF em português, os PDFs da Americanas, o provedor Anthropic com chave real, o Caddy com certificado real e a implantação num servidor.

## Registro anterior (1.3.0)

O verificador de projeto confere a integridade dos prompts e o estado inicial do catálogo. Os testes automatizados usam dados sintéticos e um runtime simulado. Veja os comandos em [README.md](../README.md) e o diagnóstico em [INSTALAR_NO_NOTEBOOK.md](../INSTALAR_NO_NOTEBOOK.md).

A cópia de migração de 13/11/2026 passou na integridade inicial, em 165 testes automatizados e na abertura HTTP com catálogo vazio, sem iniciar o modelo. O ensaio usou o Python disponível na estação de preparação. Instalação e login na estação de destino precisam ser verificados após a transferência.
