# Implantação do piloto hospedado

Guia para publicar a Mesa de apuração no **modo piloto**: acesso só por convite, interface em inglês por padrão (o botão **Português** troca o idioma) e inferência pela API do provedor escolhido. Este pacote **não foi implantado nem testado num servidor real**; os testes automatizados cobrem o modo piloto localmente (`testes/test_acesso.py`).

## O que vai para o servidor

| Peça | Arquivo | Papel |
| --- | --- | --- |
| Aplicação | `Dockerfile` | Python 3.12, `requirements.txt` + leitura visual opcional (PyMuPDF), usuário sem privilégio, `HEALTHCHECK` em `/saude` |
| Orquestração | `docker-compose.yml` | Serviço `vlado` (modo piloto) e `caddy` (HTTPS automático) |
| Proxy HTTPS | `deploy/Caddyfile` | Certificado automático para `VLADO_DOMINIO`; repassa o `Host` original |
| Variáveis | `.env.example` → `.env` | Domínio, versão da imagem e, opcionalmente, a chave da API |
| Dados | volumes Docker | `casos`, `conversas`, `execucoes`, `lixeira`, `entrada`, `segredos`, `ajustes`, `acesso` |

Requisitos do servidor: Docker com Compose v2, portas 80 e 443 abertas, um domínio com DNS apontando para o servidor. Uma VPS pequena (2 vCPU, 4 GB de RAM, 20 GB de disco) deve bastar para um acervo pequeno e poucos convidados; confirme preços e região antes de contratar.

## Primeira implantação

1. Copie o repositório para o servidor e crie o `.env`:
   ```bash
   cp .env.example .env
   ```
   Edite `VLADO_DOMINIO` (ex.: `vlado.suaredacao.org`) e `VLADO_VERSAO` (ex.: `1.4.0`).
2. Suba os serviços:
   ```bash
   docker compose up -d --build
   ```
   Confira: `docker compose ps` deve mostrar `vlado` como `healthy`; `https://SEU_DOMINIO/` responde **401 — acesso somente por convite**.
3. Crie o primeiro administrador. O link aparece **uma única vez**:
   ```bash
   docker compose exec vlado python scripts/acesso.py criar-admin --nome "Grupo VLADO" --origem "https://SEU_DOMINIO"
   ```
4. Abra o link no navegador. Em **Perguntar à IA › Conexão e opções**, escolha o provedor, opcionalmente o modelo, cole a chave da API e salve. A chave fica no volume `segredos` e nunca volta ao navegador; o painel mostra só os 4 últimos caracteres. Alternativa: definir `ANTHROPIC_API_KEY` ou `OPENAI_API_KEY` no `.env` (tem prioridade sobre a chave salva).
5. Cadastre o acervo (área **Cadastrar documentos**) e confira o recibo, como no uso local.

## Convites

- Em **Apurações e lixeira › Convites do piloto**, informe nome, apurações liberadas, consultas por dia e validade. O link aparece uma vez; envie-o por um canal privado.
- O convidado só vê **Perguntar à IA**, só nas apurações liberadas, e só as conversas que ele mesmo criou. Não cadastra documentos, não muda provedor nem chave e não encerra o serviço.
- **Revogar** encerra as sessões daquele convite na próxima requisição. Pela linha de comando:
  ```bash
  docker compose exec vlado python scripts/acesso.py listar
  ```
  ```bash
  docker compose exec vlado python scripts/acesso.py revogar ID_DO_CONVITE
  ```
- Sessões duram 12 horas (ou até o fim da validade do convite). Os tokens de convite e de sessão ficam guardados só como hash.

## Limites de gasto

`configuracao.json` → `"limites"`: `tokens_por_consulta` (padrão 3.000.000) e `tokens_por_dia` (padrão 30.000.000, somando toda a instalação). Uma rodada que ultrapassa o limite é interrompida com erro claro; perguntas novas são recusadas quando o limite diário foi atingido. Cada convite tem ainda sua cota diária de perguntas. **Configure também o teto de gasto na conta do provedor**: é a única barreira que vale mesmo se o servidor falhar. O consumo de cada chamada fica em `execucoes/<caso>/<rodada>/saidas/api_uso_NNNN.json`.

## Backup e restauração

Faça backup antes de cada atualização e diariamente durante a janela do piloto. As chaves salvas ficam fora do backup, a menos que você peça `--incluir-segredos`.

```bash
docker compose exec -T vlado python scripts/backup.py criar --destino - > vlado-dados-$(date +%Y%m%d).tar.gz
```

Restaurar (em instalação vazia, ou trocando os dados atuais com `--substituir`):

```bash
docker compose exec -T vlado python scripts/backup.py restaurar - --substituir < vlado-dados-AAAAMMDD.tar.gz
```

Guarde os arquivos fora do servidor. Ensaie uma restauração antes de liberar o link (checklist do escopo, seção 8).

## Atualizar e reverter

1. Backup (seção anterior).
2. Atualize o código, mude `VLADO_VERSAO` no `.env` (ex.: `1.4.1`) e rode `docker compose up -d --build`. A imagem anterior continua disponível com a tag antiga.
3. Para reverter: volte `VLADO_VERSAO` à tag anterior e rode `docker compose up -d` (sem `--build`). Os volumes não mudam; se a versão nova alterou dados de forma incompatível, restaure o backup.

## Limitações conhecidas

- O cancelamento interrompe a execução entre eventos da resposta; uma chamada já presa na API só termina pelo prazo do SDK (até 600 s por tentativa).
- Os dados (documentos, conversas, histórico enviado ao provedor) ficam em texto claro nos volumes; proteja o servidor e defina por quanto tempo guardá-los.
- O processamento pelo modelo é online, no provedor escolhido, sujeito à política de retenção da conta.
- Os arquivos `.cmd`/`.vbs` e o guia de instalação Windows valem só para o uso local.
