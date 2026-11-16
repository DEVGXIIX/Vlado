# Instalador Windows (Vlado-Setup.exe)

O `Vlado-Setup.exe` instala a Mesa do Vlado num computador Windows 10/11 (64 bits), por usuário, sem pedir administrador. Já vem com tudo: o `Vlado.exe` (Python, OCRmyPDF e demais bibliotecas embutidos), o Tesseract com os idiomas português, inglês e detecção de orientação (`por`, `eng`, `osd`) e o Ghostscript. Nada depende do PATH do sistema nem de instalações prévias.

## Arquivo desta versão

| Item | Valor |
| --- | --- |
| Arquivo | `dist/Vlado-Setup.exe` (gerado; fora do git) |
| Versão | 2.0.0 |
| Tamanho | 127,1 MB (133.244.422 bytes) |
| SHA-256 | `6a6dd8df62b58c64fa2c8edb74e4f6cab2d35737db2872482bac38f298a3d625` |

Confira o hash antes de instalar, no PowerShell:

```powershell
Get-FileHash .\Vlado-Setup.exe -Algorithm SHA256
```

## Aviso do SmartScreen (instalador sem assinatura)

O instalador ainda **não tem assinatura de código**. Na primeira execução o Windows pode mostrar "O Windows protegeu o computador". Depois de conferir o SHA-256 acima, clique em **Mais informações** e em **Executar assim mesmo**. A pendência é obter um certificado de assinatura de código (OV ou EV) e assinar o `Vlado.exe` e o `Vlado-Setup.exe` com `signtool`.

## O que a instalação faz

- Programa em `%LOCALAPPDATA%\Programs\Vlado` (`Vlado.exe`, `tesseract\`, `ghostscript\`, `licencas\`).
- Atalhos no Menu Iniciar (Vlado e Desinstalar Vlado) e, se marcado, na área de trabalho.
- Desinstalador em Configurações > Aplicativos.
- Dados em `%LOCALAPPDATA%\Vlado`: `casos\`, `conversas\`, `execucoes\`, `acesso\` (contas e sessões), `segredos\chaves.json`, `logs\`. Essa pasta é criada pelo próprio Vlado e **é preservada na atualização e na desinstalação**. Para apagar tudo, remova-a à mão depois de desinstalar.

Instalação silenciosa (por exemplo, para TI): `Vlado-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER`. Desinstalação silenciosa: `unins000.exe /VERYSILENT` na pasta do programa.

## Primeira abertura

1. Abra o **Vlado** pelo Menu Iniciar ou pela área de trabalho. Não aparece janela de terminal: o Vlado sobe o servidor em `http://127.0.0.1:<porta>` (8765 quando livre) e abre o navegador padrão.
2. Sem nenhuma conta, a página mostra **Criar administrador**: nome, login, senha (mínimo 12 caracteres) e confirmação. Essa tela só aceita o próprio computador e desaparece de vez depois da primeira conta.
3. Entre com o login criado. Daí em diante, toda abertura pede login e senha (sessão de até 12 h, encerrada após 2 h sem uso; 5 erros seguidos bloqueiam o login por 15 min).
4. Em **Configurações** (só para a administração), crie contas para outras pessoas: convidado (só pergunta à IA, nas apurações liberadas, com cota diária) ou administração. O link de ativação vale para este computador (`http://127.0.0.1:<porta>/ativar/...`).
5. Configure provedor e chave da API em **Perguntar à IA**; a chave fica em `%LOCALAPPDATA%\Vlado\segredos\chaves.json`.

Abrir o Vlado de novo com ele já aberto só reabre o navegador (uma instância por usuário). Para encerrar, use **Encerrar serviço** em Perguntar à IA.

## OCR embutido

O `Vlado.exe` aponta o OCR para as cópias instaladas por `VLADO_TESSERACT`, `VLADO_TESSDATA` e `VLADO_GHOSTSCRIPT` e usa `por+eng`. O OCRmyPDF roda dentro do próprio `Vlado.exe` (`Vlado.exe -m ocrmypdf`), sem janela de console. O texto de OCR continua sujeito a erros e não substitui a conferência no original.

## Gerar o instalador

Requisitos: Windows 64 bits, Python 3.12 em `.venv` com `requirements.txt` e `pyinstaller==6.16.0`.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.16.0
.venv\Scripts\python.exe scripts\gerar_instalador.py
```

O script baixa as dependências de `instalador/dependencias.json` (versão e SHA-256 fixados; arquivo divergente é recusado) para `.ferramentas\downloads`, extrai Tesseract e Ghostscript dos instaladores originais com 7-Zip (sem executá-los), monta `build\instalador\payload`, congela o `Vlado.exe` com `instalador\vlado.spec` (`console=False`) e compila `instalador\vlado.iss` com Inno Setup 6.5.4 (instalado por usuário em `.ferramentas\innosetup`). Saída: `dist\Vlado-Setup.exe` e `dist\Vlado-Setup.exe.sha256`. Nenhuma etapa abre janela de console.

Arquivos: `scripts/vlado_lancador.py` (lançador), `instalador/vlado.spec`, `instalador/vlado.iss`, `instalador/dependencias.json`, `scripts/gerar_instalador.py`. Avisos de licença: `docs/AVISOS_DE_LICENCA.md`.

## Pendências

- Certificado de assinatura de código (SmartScreen).
- O link de ativação de convidados usa a porta do momento; se a porta mudar (8765 ocupada), gere um novo link.
