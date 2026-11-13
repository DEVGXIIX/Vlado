# Instalar no notebook Windows

## 1. Extrair a pasta

Transfira `Apuracao-1.0-piloto.zip` e use **Extrair tudo** no Windows. Mantenha a pasta inteira em um local com permissão de escrita, por exemplo Documentos. Não execute os arquivos de dentro do ZIP. Esta distribuição foi preparada para Windows; os iniciadores `.cmd` e `.vbs` não se aplicam a macOS ou Linux.

## 2. Preparar Python e Codex

Instale **Python 3.12 ou superior**, com `pip` e `venv`, a partir do [site oficial do Python](https://www.python.org/downloads/windows/). Depois da instalação, feche e reabra o terminal. O preparador tenta localizar Python pelo launcher `py`, por `python` e pelo runtime do Codex, quando disponível; não depende de um nome de usuário fixo.

Instale o **Codex CLI nativo para Windows** seguindo a seção Windows da [documentação oficial OpenAI de instalação](https://learn.chatgpt.com/docs/codex/cli). É necessário ter um `codex.exe` que suporte `app-server`. A integração do projeto não executa wrappers `.cmd`, `.bat` ou `.ps1` como processo Codex.

Se o programa estiver instalado mas não for localizado, defina a variável de usuário `APURACAO_CODEX_BIN` para o caminho completo do **seu** `codex.exe`, pelas configurações de variáveis de ambiente do Windows. Feche e reabra a Mesa depois. Não aponte para `codex.cmd`. A compatibilidade do runtime instalado no notebook deve ser conferida antes da primeira pergunta; a preparação deste pacote não valida versões futuras do protocolo.

O login é feito na própria interface, em **Perguntar ao Codex → Conexão e opções → Entrar com ChatGPT**. Use a conta do notebook; credenciais não são transportadas no ZIP. A documentação oficial descreve a [entrada com ChatGPT](https://learn.chatgpt.com/docs/codex/cli). O projeto não requer uma chave de API para esse fluxo. Acesso a modelos e limites dependem da conta e do serviço.

## 3. Executar o preparador

Abra **Preparar notebook.cmd**. Ele verifica Python e SQLite/FTS5, cria um ambiente `.venv` dentro da pasta e instala `pypdf`, `python-docx`, `reportlab` e a dependência de leitura visual de PDF. Requer conexão à internet para baixar as bibliotecas. Não instala o Codex, não configura a conta e não envia perguntas.

Em instalações corporativas, use as permissões e políticas fornecidas pela equipe de TI. O preparador não altera a política do PowerShell e não exige executar toda a Mesa como administrador.

Para um diagnóstico sem instalar nada, abra um terminal nesta pasta e execute:

```bat
"Preparar notebook.cmd" --verificar
```

Para preparar apenas o fluxo textual, deixando de instalar a biblioteca visual opcional:

```bat
"Preparar notebook.cmd" --somente-texto
```

Se a criação ou instalação falhar, o preparador informa o erro e mantém os arquivos recebidos. Execute novamente após corrigir a causa. Não copie uma `.venv` de outro computador: ela contém caminhos próprios daquela instalação.

## 4. Conferir e abrir

Antes do primeiro uso, abra **Verificar pacote.cmd**. O manifesto SHA-256 verifica os arquivos desta distribuição. Após editar configurações ou cadastrar apurações, mudanças de hash nesses arquivos são esperadas; este verificador é uma conferência do pacote inicial, não uma validação editorial nem um monitor do seu trabalho.

Abra **Abrir mesa.vbs**. O navegador acessa `http://127.0.0.1:8765`. A alternativa com console é **Iniciar pesquisa.cmd**. O servidor escuta somente no próprio computador; não é necessário encaminhar portas do roteador. Se o navegador não abrir, acesse esse endereço manualmente depois de iniciar o servidor.

Se a porta estiver ocupada por outra Mesa, encerre o serviço anterior em **Conexão e opções → Encerrar serviço**, depois reabra a pasta correta. Não interrompa uma execução que precisa preservar. Para escolher outra porta, execute:

```bat
"Iniciar pesquisa.cmd" --porta 8766
```

## 5. Começar o piloto

O início correto mostra **nenhuma apuração cadastrada**. Crie uma nova, envie os arquivos, confira todos os itens do recibo e só então faça a pergunta. Cada caso mantém seus próprios documentos e rodadas. As marcações humanas são declarações do operador; não constituem autenticação individual nem revisão independente.

Para retomar outro dia, abra a mesma pasta e a Mesa. Antes de copiar uma pasta já usada para outro computador, salve notas, aguarde o fim das execuções e encerre o serviço. Faça backup da pasta inteira; o ZIP inicial é apenas a distribuição vazia.

## Diagnóstico técnico

Com o ambiente preparado, os comandos abaixo verificam o fluxo e o estado inicial, sem acionar o modelo:

```bat
.venv\Scripts\python.exe scripts\montar_fluxo.py --check
.venv\Scripts\python.exe scripts\verificar_projeto.py
```

A suíte de desenvolvimento está incluída. Para executá-la, também é necessário Node.js, usado pelas regressões de JavaScript; Node não é uma dependência do servidor Python da Mesa. Testes de navegador adicionais exigem Playwright. Esses testes são opcionais para o uso cotidiano.

Documentação de instalação consultada em 10/11/2026. O comportamento no notebook, a disponibilidade dos modelos e o login dependem do ambiente de destino e precisam ser conferidos nele.
