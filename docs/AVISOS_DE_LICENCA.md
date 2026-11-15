# Avisos de licença

Componentes de terceiros distribuídos neste pacote ou instalados pela imagem Docker e pelo app Android. Os textos completos das licenças vendorizadas acompanham os arquivos indicados.

## Licença do próprio Vlado

**Pendente.** O repositório não declara licença para o código do Vlado. Até o grupo decidir, o pacote é entregue ao Intercept para avaliação e piloto, sem concessão de redistribuição. Decisão em aberto na seção 12 de `Começar_Analise_Aqui.md`.

## Distribuídos no pacote (interface)

| Componente | Licença | Texto |
| --- | --- | --- |
| Vditor 4.0.1 (inclui Lute) | MIT | `interface/vendor/vditor/LICENSE` |
| pdf.js (pdfjs-dist) | Apache-2.0 | `interface/vendor/pdfjs/LICENSE` |
| Source Serif 4 | SIL Open Font License 1.1 | `interface/fonts/LICENSE-SourceSerif4.md` |
| Source Sans 3 | SIL Open Font License 1.1 | `interface/fonts/LICENSE-SourceSans3.md` |

## Instalados no servidor (requirements.txt e Dockerfile)

| Componente | Licença | Observação |
| --- | --- | --- |
| pypdf | BSD-3-Clause | |
| OCRmyPDF | MPL-2.0 | |
| PyMuPDF | **AGPL-3.0** (ou licença comercial da Artifex) | Num serviço acessível pela rede, a AGPL exige oferecer o código-fonte correspondente aos usuários. O código do Vlado está neste pacote; confirme com o jurídico se isso atende, ou retire o PyMuPDF (a leitura visual de páginas pelo modelo fica indisponível; o OCR segue pelo OCRmyPDF). |
| Ghostscript (apt) | **AGPL-3.0** | Usado pelo OCRmyPDF como programa externo, sem modificação. |
| Tesseract OCR (apt) | Apache-2.0 | |
| python-docx | MIT | |
| ReportLab | BSD-3-Clause | |
| anthropic (SDK) | MIT | |
| openai (SDK) | Apache-2.0 | |
| argon2-cffi | MIT | |
| Caddy 2.8 (imagem) | Apache-2.0 | |
| Python 3.12 (imagem base) | PSF License | |

## App Android

| Componente | Licença |
| --- | --- |
| Kotlin, AndroidX (WebKit, AppCompat, Core) | Apache-2.0 |

Versões exatas: `requirements.txt`, `android/app/build.gradle.kts` e `interface/vendor/*/manifesto.json`.
