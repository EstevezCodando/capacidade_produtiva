# Implantação no Windows Server — Capacidade Produtiva

Guia passo a passo para levantar o sistema pela primeira vez em um Windows Server.

---

## Banco CP — interno ou externo?

O sistema suporta duas configurações para o banco de dados do CP:

| Opção | Quando usar |
|-------|-------------|
| **Banco interno** (Docker cria) | Nova instalação, sem PostgreSQL existente |
| **Banco externo** (servidor existente) | Já existe um PostgreSQL com dados do CP em outra máquina |

O `setup.ps1` pergunta qual opção usar e configura tudo automaticamente.

---

## Arquitetura da stack

**Banco CP interno (opção 1):**

```
Windows Server (esta maquina)
  frontend (nginx :5173)
    |
  backend (FastAPI :3050)
    |-- cp_db (PostgreSQL interno, Docker)
    |-- SAP DB (PostgreSQL externo, read-only)
    |-- Auth Service (outra maquina)
```

**Banco CP externo (opção 2):**

```
Windows Server (esta maquina)
  frontend (nginx :5173)
    |
  backend (FastAPI :3050)
    |-- CP DB (PostgreSQL externo existente)
    |-- SAP DB (PostgreSQL externo, read-only)
    |-- Auth Service (outra maquina)
```

**O que sempre roda no Docker:**
- `backend` — API FastAPI com Alembic e sincronização SAP
- `frontend` — React compilado, servido pelo nginx

**O que é sempre externo:**
- Banco SAP — PostgreSQL em outra máquina, acesso somente-leitura
- Serviço de autenticação — API em outra máquina que emite e valida JWT

---

## Fluxo obrigatório (ordem)

```
1. Instalar Docker Desktop
2. Baixar o projeto
3. Executar setup.ps1   →  gera o .env automaticamente
4. docker compose up -d --build  →  sobe o sistema
```

---

## Informações necessárias antes de começar

Reúna esses dados com as equipes responsáveis antes de iniciar:

| Dado | Onde obter |
|------|-----------|
| **Se banco CP externo:** IP/hostname do servidor CP | Equipe de infraestrutura |
| **Se banco CP externo:** Nome do banco, usuário e senha | DBA |
| IP ou hostname do servidor SAP | Equipe de infraestrutura |
| Porta do PostgreSQL SAP | Normalmente `5432` |
| Nome do banco SAP | Equipe SAP |
| Usuário e senha (somente-leitura) do banco SAP | DBA / equipe SAP |
| URL do serviço de autenticação | Ex: `http://192.168.1.50:3001` |
| Usuário e senha do administrador no auth service | Responsável pelo auth service |

---

## Pré-requisitos

### Docker Desktop instalado no Windows Server

Baixe em: https://www.docker.com/products/docker-desktop/

Após instalar, verifique no PowerShell (como Administrador):

```powershell
docker --version
docker compose version
```

Ambos devem retornar versão sem erro.

### Código do projeto disponível

```powershell
git clone <url-do-repositorio> C:\Sistemas\capacidade_produtiva
cd C:\Sistemas\capacidade_produtiva
```

---

## Simulação completa do deploy

A seguir, duas simulações: nova instalação (banco interno) e integração com banco existente.

---

### Simulação A — Nova instalação (banco interno)

> **Dados usados:**
> - Banco CP: criado pelo Docker automaticamente
> - Banco SAP: `192.168.10.50:5432` / banco `sap_producao` / usuário `cp_readonly`
> - Auth service: `http://192.168.10.30:3001` / admin `joao.silva`

```powershell
PS C:\Sistemas\capacidade_produtiva> powershell -ExecutionPolicy Bypass -File setup.ps1
```

```
============================================================
   Capacidade Produtiva - Configuracao inicial
============================================================

Este script coleta as informacoes necessarias e gera
o arquivo .env para voce executar o Docker em seguida.


--- Banco de dados do Capacidade Produtiva ---

  Opcoes:
    1 - Criar banco interno (gerenciado pelo Docker, recomendado para nova instalacao)
    2 - Usar banco externo ja existente (outro servidor PostgreSQL)

  Escolha [1/2]: 1

  O Docker vai criar e gerenciar o banco automaticamente.
  Escolha um nome de usuario e senha para ele.

Nome do banco [capacidade_produtiva]: Enter
Usuario do banco [cp_user]: Enter
Senha do banco (escolha uma senha forte) (oculto): ************
  OK  Banco interno configurado (Docker ira criar o PostgreSQL)

Porta da API [3050]: Enter
Porta do frontend [5173]: Enter


--- Banco de dados SAP (externo, somente leitura) ---

IP ou hostname do servidor SAP: 192.168.10.50
Porta do PostgreSQL SAP [5432]: Enter
Nome do banco SAP: sap_producao
Usuario somente-leitura do banco SAP: cp_readonly
Senha do usuario SAP (oculto): ************

  Testando conexao com o banco SAP...
  OK  Banco SAP acessivel


--- Servico de Autenticacao ---

URL do servico de autenticacao (ex: http://192.168.1.50:3001): http://192.168.10.30:3001
  Testando conexao...
  OK  Servico de autenticacao operacional

Usuario administrador do auth service: joao.silva
Senha do administrador (oculto): ************
  Autenticando...
  OK  Login realizado com sucesso

  Gerando chaves de seguranca automaticamente...
  OK  Chaves geradas

============================================================
   Configuracao concluida! Arquivo .env gerado.
============================================================

  Banco CP: interno (Docker vai criar o PostgreSQL automaticamente)

Proximo passo - subir o sistema:

   docker compose up -d --build
```

---

### Simulação B — Banco CP externo já existente

> **Dados usados:**
> - Banco CP externo: `192.168.10.20:5432` / banco `capacidade_produtiva` / usuário `cp_user`
> - Banco SAP: `192.168.10.50:5432` / banco `sap_producao` / usuário `cp_readonly`
> - Auth service: `http://192.168.10.30:3001` / admin `joao.silva`

```powershell
PS C:\Sistemas\capacidade_produtiva> powershell -ExecutionPolicy Bypass -File setup.ps1
```

```
============================================================
   Capacidade Produtiva - Configuracao inicial
============================================================

  Escolha [1/2]: 2

  Informe os dados de conexao do PostgreSQL existente.

IP ou hostname do servidor PostgreSQL do CP: 192.168.10.20
Porta do PostgreSQL do CP [5432]: Enter
Nome do banco de dados do CP [capacidade_produtiva]: Enter
Usuario do banco do CP: cp_user
Senha do usuario (oculto): ************

  Testando conexao com 192.168.10.20:5432...
  OK  Banco CP acessivel
  OK  Banco externo configurado

Porta da API [3050]: Enter
Porta do frontend [5173]: Enter

[... continua igual com SAP e Auth ...]

============================================================
   Configuracao concluida! Arquivo .env gerado.
============================================================

  Banco CP: externo em 192.168.10.20:5432

Proximo passo - subir o sistema:

   docker compose up -d --build
```

O comando `docker compose up` é **o mesmo nos dois casos** — o `.env` gerado pelo script já diz ao Docker o que subir.

PS C:\Sistemas\capacidade_produtiva>
```

O arquivo `.env` foi criado automaticamente com todas as variáveis preenchidas e encoding correto.

---

### PASSO 3 — Subir o Docker

```powershell
PS C:\Sistemas\capacidade_produtiva> docker compose up -d --build
```

```
[+] Building...
 ✔ backend   — imagem Python compilada      8.3s
 ✔ frontend  — imagem Node/Vite compilada  45.2s

[+] Running 3/3
 ✔ Container cp_db     Started   2.1s
 ✔ Container backend   Started   3.4s
 ✔ Container frontend  Started   1.2s

PS C:\Sistemas\capacidade_produtiva>
```

O primeiro build demora entre **3 e 10 minutos** dependendo da velocidade da conexão.

---

### PASSO 4 — Acompanhar a inicialização

```powershell
PS C:\Sistemas\capacidade_produtiva> docker compose logs -f backend
```

```
backend  | ══════════════════════════════════════════════════════════════
backend  |   ► Migrações Alembic (upgrade head)
backend  | ══════════════════════════════════════════════════════════════
backend  | INFO  [alembic] Running upgrade  -> 0001, init schema
backend  | INFO  [alembic] Running upgrade 0001 -> 0002, parametros
backend  | ...
backend  | INFO  [alembic] Running upgrade 0011 -> 0012, teto_sexta_e_extra
backend  |
backend  | ══════════════════════════════════════════════════════════════
backend  |   ► Sincronização SAP → sap_snapshot
backend  | ══════════════════════════════════════════════════════════════
backend  |   ✔ Sincronização SAP concluída.
backend  |
backend  | ══════════════════════════════════════════════════════════════
backend  |   ► API CapacidadeProdutiva  →  http://0.0.0.0:3050
backend  | ══════════════════════════════════════════════════════════════
backend  |   CP_API_PORT  = 3050
backend  |   ENVIRONMENT  = production
backend  |   CP_DB_HOST   = cp_db
backend  |
backend  | INFO:     Application startup complete.
backend  | INFO:     Uvicorn running on http://0.0.0.0:3050
```

Pressione **Ctrl+C** para sair dos logs sem parar os containers.

---

### PASSO 5 — Verificar que tudo está rodando

```powershell
PS C:\Sistemas\capacidade_produtiva> docker compose ps
```

```
NAME         STATUS
cp_db        running (healthy)
backend      running (healthy)
frontend     running (healthy)
```

---

### PASSO 6 — Testar e acessar o sistema

```powershell
PS C:\Sistemas\capacidade_produtiva> Invoke-WebRequest -Uri http://localhost:3050/api/health -UseBasicParsing

StatusCode : 200
Content    : {"status":"ok"}
```

Abra o navegador e acesse **`http://localhost:5173`**.

A tela de login aparece. Use o mesmo usuário e senha do serviço de autenticação.

---

## Cenários de erro e como resolver

### Erro: senha do auth service errada

O script não deixa prosseguir e encerra com a mensagem:

```
  Autenticando...
ERRO  Falha na autenticacao: Credenciais invalidas
  Verifique o usuario e senha e execute o script novamente.
```

Execute `setup.ps1` novamente com as credenciais corretas.

---

### Erro: banco SAP inacessível

O script avisa mas continua gerando o `.env`:

```
  Testando conexao com o banco SAP...
  AVISO: Nao foi possivel conectar em 192.168.10.50:5432
  Verifique o firewall. O setup continuara mesmo assim.
```

O Docker sobe, mas a sincronização SAP falha nos logs:

```
backend  |   ⚠  Sincronização SAP falhou — API sera iniciada com dados existentes.
backend  |      Verifique as variáveis SAP_DB_* e a conectividade com o banco SAP.
```

A API funciona normalmente. Para corrigir: ajuste o IP/credenciais no `.env` e reinicie:

```powershell
docker compose up -d
```

---

### Erro: porta 5433 bloqueada pelo Windows

```
Error: ports are not available: exposing port TCP 127.0.0.1:5433
bind: An attempt was made to access a socket in a way forbidden by its access permissions.
```

Verifique quais portas estão reservadas pelo Hyper-V:

```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```

Edite o `docker-compose.yml` e mude a porta do serviço `cp_db` para uma porta livre:

```yaml
ports:
  - "127.0.0.1:5434:5432"   # troque 5433 por qualquer porta livre
```

Suba novamente:

```powershell
docker compose up -d --build
```

---

### Erro: backend em loop de restart

```powershell
docker compose logs backend | Select-Object -Last 30
```

| Mensagem no log | Solução |
|-----------------|---------|
| `CP_SECRET_KEY deve ser definido em produção` | Execute `setup.ps1` novamente |
| `JWT_SECRET deve ser definido em produção` | Execute `setup.ps1` novamente |
| `AUTH_URL deve ser definido em produção` | Execute `setup.ps1` novamente |
| `could not connect to server` (SAP) | Verificar IP e firewall do banco SAP |
| `password authentication failed` | Usuário/senha errados — execute `setup.ps1` novamente |
| `relation does not exist` | `docker compose exec backend python -m alembic upgrade head` |

---

## Operações do dia a dia

### Parar os containers

```powershell
docker compose down
# Os dados do banco ficam preservados no volume cp_db_data
```

### Reiniciar

```powershell
docker compose up -d
```

### Ver logs

```powershell
docker compose logs -f backend          # tempo real
docker compose logs --tail=100 backend  # últimas 100 linhas
```

### Atualizar após nova versão do código

```powershell
git pull
docker compose build
docker compose up -d
```

### Sincronização SAP manual

```powershell
docker compose exec backend sincronizar-sap
```

### Verificar migrations

```powershell
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic upgrade head
```

### Limpar imagens antigas (não apaga dados)

```powershell
docker image prune -f
```

---

## Referência rápida de variáveis do `.env`

Geradas automaticamente pelo `setup.ps1`. Edite apenas se necessário corrigir algum valor.

| Variável | Descrição |
|----------|-----------|
| `ENVIRONMENT` | `production` — ativa as validações de segurança |
| `CP_DB_HOST` | `cp_db` (banco interno) ou IP do servidor externo |
| `CP_DB_PORT` | Porta do banco CP (padrão: `5432`) |
| `CP_DB_NAME` | Nome do banco do CP |
| `CP_DB_USER` | Usuário do banco do CP |
| `CP_DB_PASSWORD` | Senha do banco do CP |
| `CP_API_PORT` | Porta da API (padrão: `3050`) |
| `FRONTEND_PORT` | Porta do frontend (padrão: `5173`) |
| `CP_SECRET_KEY` | Gerado automaticamente pelo `setup.ps1` |
| `SAP_DB_HOST` | IP ou hostname do servidor PostgreSQL SAP |
| `SAP_DB_PORT` | Porta do banco SAP (padrão: `5432`) |
| `SAP_DB_NAME` | Nome do banco SAP |
| `SAP_DB_USER` | Usuário somente-leitura do banco SAP |
| `SAP_DB_PASSWORD` | Senha do usuário SAP |
| `JWT_SECRET` | Gerado automaticamente pelo `setup.ps1` |
| `AUTH_URL` | URL do serviço de autenticação |
| `AUTH_ADMIN_USER` | Usuário admin do auth service |
| `AUTH_ADMIN_PASSWORD` | Senha admin do auth service |
| `COMPOSE_PROFILES` | `local-db` = sobe banco interno; vazio = banco externo |

> `COMPOSE_PROFILES` é lido automaticamente pelo Docker Compose — não é necessário passá-lo na linha de comando.
