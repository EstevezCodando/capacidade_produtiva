# Implantação no Windows Server — Capacidade Produtiva

Guia passo a passo para levantar o sistema pela primeira vez em um Windows Server,
utilizando banco de dados PostgreSQL externo para o SAP e serviço de autenticação em outra máquina.

---

## Arquitetura da stack

```
┌─────────────────────────────────────────────────────┐
│  Windows Server (esta máquina)                      │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │ frontend │──▶│ backend  │──▶│ cp_db          │  │
│  │ nginx    │   │ FastAPI  │   │ PostgreSQL 16  │  │
│  │ :5173    │   │ :3050    │   │ (interno)      │  │
│  └──────────┘   └────┬─────┘   └────────────────┘  │
└────────────────────── │ ───────────────────────────┘
                        │
          ┌─────────────┴────────────┐
          │                          │
   ┌──────▼──────┐          ┌────────▼───────┐
   │ SAP DB      │          │ Auth Service   │
   │ PostgreSQL  │          │ (outra máquina)│
   │ (externo,   │          │ :3001          │
   │  read-only) │          └────────────────┘
   └─────────────┘
```

**O que roda nesta máquina (Docker):**
- `cp_db` — PostgreSQL 16 interno, dados do sistema CP
- `backend` — API FastAPI com Alembic e sincronização SAP
- `frontend` — React compilado, servido pelo nginx

**O que é externo (não sobe no Docker):**
- Banco SAP — PostgreSQL em outra máquina, acesso somente-leitura
- Serviço de autenticação — API em outra máquina que emite e valida JWT

---

## Pré-requisitos

### 1. Docker Desktop instalado no Windows Server

Baixe em: https://www.docker.com/products/docker-desktop/

Após instalar, verifique no PowerShell (como Administrador):

```powershell
docker --version
docker compose version
```

Ambos devem retornar versão sem erro.

### 2. Código do projeto disponível

```powershell
# Via git
git clone <url-do-repositorio> C:\Sistemas\capacidade_produtiva
cd C:\Sistemas\capacidade_produtiva

# Ou extraia o ZIP diretamente em C:\Sistemas\capacidade_produtiva
```

### 3. Informações necessárias antes de começar

Reúna esses dados com as equipes responsáveis **antes** de iniciar:

| Dado | Onde obter |
|------|-----------|
| IP ou hostname do servidor PostgreSQL SAP | Equipe de infraestrutura |
| Porta do PostgreSQL SAP | Normalmente `5432` |
| Nome do banco SAP | Equipe SAP |
| Usuário e senha (somente-leitura) do banco SAP | DBA / equipe SAP |
| URL do serviço de autenticação | Ex: `http://192.168.1.50:3001` |
| Usuário e senha do administrador no auth service | Responsável pelo auth service |
| **`JWT_SECRET` do serviço de autenticação** | Ver instrução abaixo |

#### Como obter o JWT_SECRET do serviço de autenticação

O `JWT_SECRET` é a chave criptográfica que o auth service usa para assinar os tokens de login.
O Capacidade Produtiva precisa da **mesma chave** para validar esses tokens.

Peça ao responsável pelo serviço de autenticação para abrir o arquivo de configuração
do serviço (normalmente chamado `config.env` ou `.env` na pasta de instalação dele)
e copiar o valor da linha:

```
JWT_SECRET=valor_da_chave_aqui
```

Esse valor será solicitado durante a configuração interativa no Passo 2.

> **Por que não é buscado automaticamente?**
> Por segurança, nenhum serviço expõe sua chave secreta via API.
> Ela deve ser copiada diretamente do arquivo de configuração do auth service
> e repassada de forma segura (pessoalmente ou via canal seguro).

---

## Passo 1 — Abrir o PowerShell como Administrador

Clique em Iniciar → pesquise "PowerShell" → botão direito → **Executar como administrador**.

```powershell
cd C:\Sistemas\capacidade_produtiva
```

---

## Passo 2 — Executar a configuração interativa

O sistema possui um assistente de configuração que coleta todas as informações,
testa as conexões, autentica no auth service e gera o arquivo `.env` automaticamente.

Execute:

```powershell
docker compose run --rm backend uv run configurar
```

> Se ainda não tiver a imagem buildada, execute primeiro:
> ```powershell
> docker compose build backend
> docker compose run --rm backend uv run configurar
> ```

O assistente vai perguntar, **nesta ordem**:

```
=== CapacidadeProdutiva — Configuração inicial ===

--- Banco de dados CapacidadeProdutiva ---
Endereço do servidor PostgreSQL do CP [localhost]:
Porta do PostgreSQL do CP [5432]:
Nome do banco de dados do CP [capacidade_produtiva]:
Usuário PostgreSQL do CP:
Senha do usuário PostgreSQL do CP:
Deseja criar o banco de dados do CP agora? (S/n):

--- Banco de dados SAP (somente leitura) ---
Endereço do servidor PostgreSQL do SAP:
Porta do PostgreSQL do SAP [5432]:
Nome do banco de dados do SAP:
Usuário PostgreSQL do SAP (somente leitura):
Senha do usuário PostgreSQL do SAP:

--- Serviço de Autenticação ---
URL do servico_autenticacao (ex: http://192.168.0.10:3010):
  ✓ servico_autenticacao operacional
Usuário do servico_autenticacao (será admin do CP):
Senha do usuário:
  ✓ Login OK

--- Chave de segurança JWT ---
JWT_SECRET do servico_autenticacao:   ← cole aqui o valor do config.env do auth service
  ✓ CP_SECRET_KEY gerado automaticamente

--- Configuração da aplicação ---
Porta do servidor CapacidadeProdutiva [3050]:

Gravando config.env...
  ✓ config.env criado com sucesso
```

Ao final, o arquivo `config.env` é gerado automaticamente na pasta do projeto com todas as variáveis preenchidas.

---

## Passo 3 — Renomear o arquivo de configuração

```powershell
# Renomear config.env para .env (nome padrão lido pelo Docker Compose)
Rename-Item config.env .env
```

---

## Passo 4 — Corrigir encoding do `.env` (obrigatório no Windows)

```powershell
$content = Get-Content .env -Raw
[System.IO.File]::WriteAllText(
    "$PWD\.env",
    $content,
    [System.Text.UTF8Encoding]::new($false)
)
```

Isso garante que o arquivo seja salvo em UTF-8 sem BOM, formato exigido pelo Docker.

---

## Passo 5 — Verificar se todas as variáveis estão preenchidas

```powershell
docker compose config | Select-String -Pattern "CP_DB|SAP_DB|JWT|AUTH|CP_SECRET"
```

Todas as variáveis devem aparecer com seus valores. Se alguma aparecer em branco, repita o Passo 2.

---

## Passo 6 — Verificar conectividade com os serviços externos

```powershell
# Substituir pelos IPs reais do seu ambiente
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432   # banco SAP
Test-NetConnection -ComputerName 192.168.1.50  -Port 3001   # auth service
```

A coluna `TcpTestSucceeded` deve retornar `True`. Se retornar `False`:
- Solicite à equipe de infraestrutura que libere a porta no firewall do servidor de destino para o IP deste servidor
- Verifique se a VPN ou rede está ativa

---

## Passo 7 — Build completo e primeira subida

```powershell
docker compose --env-file .env up -d --build
```

Este comando:
1. Compila a imagem do backend (Python + dependências)
2. Compila a imagem do frontend (Node.js + Vite)
3. Sobe os três containers (`cp_db`, `backend`, `frontend`)

O primeiro build demora de **3 a 10 minutos** dependendo da conexão com a internet.

---

## Passo 8 — Acompanhar a inicialização

```powershell
# Ver logs em tempo real (Ctrl+C para sair sem parar os containers)
docker compose logs -f backend
```

Sequência normal de inicialização:

```
backend  | Running Alembic migrations...
backend  | INFO  [alembic.runtime.migration] Running upgrade ...
backend  | Migrations complete.
backend  | Running SAP sync...
backend  | SAP sync complete.
backend  | INFO:     Application startup complete.
backend  | INFO:     Uvicorn running on http://0.0.0.0:3050
```

---

## Passo 9 — Verificar status dos containers

```powershell
docker compose ps
```

Resultado esperado:

```
NAME         STATUS
cp_db        running (healthy)
backend      running (healthy)
frontend     running (healthy)
```

Se algum mostrar `restarting`, veja os logs: `docker compose logs backend`

---

## Passo 10 — Testar o sistema

```powershell
# Testar a API
Invoke-WebRequest -Uri http://localhost:3050/api/health -UseBasicParsing
# Deve retornar StatusCode 200
```

Abra o navegador: **`http://localhost:5173`**

A tela de login deve aparecer. Use as mesmas credenciais do serviço de autenticação.

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
# As migrations rodam automaticamente no start
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

---

## Solução de problemas

### `.env` não encontrado ou variáveis em branco

```powershell
# Verificar se o arquivo não é .env.txt (extensão oculta)
Get-ChildItem | Where-Object { $_.Name -like "*env*" }

# Se for .env.txt, renomear:
Rename-Item .env.txt .env

# Reaplicar correção de encoding:
$content = Get-Content .env -Raw
[System.IO.File]::WriteAllText("$PWD\.env", $content, [System.Text.UTF8Encoding]::new($false))
```

### Backend reiniciando em loop

```powershell
docker compose logs backend | Select-Object -Last 30
```

| Mensagem no log | Causa | Solução |
|-----------------|-------|---------|
| `CP_SECRET_KEY deve ser definido em produção` | Campo vazio no `.env` | Repetir Passo 2 |
| `JWT_SECRET deve ser definido em produção` | Campo vazio no `.env` | Repetir Passo 2 |
| `AUTH_URL deve ser definido em produção` | Campo vazio no `.env` | Repetir Passo 2 |
| `could not connect to server` (SAP) | Firewall ou IP errado | Verificar Passo 6 |
| `password authentication failed` | Usuário/senha errados | Corrigir no `.env` |
| `relation does not exist` | Migration não rodou | `docker compose exec backend python -m alembic upgrade head` |

### Login falha com "token inválido"

O `JWT_SECRET` no `.env` está diferente do `JWT_SECRET` do auth service.

```powershell
# Verificar o valor atual no .env
Select-String -Path .env -Pattern "JWT_SECRET"
```

Entre em contato com o responsável pelo auth service, obtenha o valor correto do
`JWT_SECRET` do arquivo de configuração dele e atualize o `.env`. Depois:

```powershell
docker compose up -d   # reinicia com o novo valor
```

### Banco SAP não conecta

```powershell
# Testar de dentro do container
docker compose exec backend python -c "
import psycopg2, os
conn = psycopg2.connect(
    host=os.environ['SAP_DB_HOST'],
    port=os.environ['SAP_DB_PORT'],
    dbname=os.environ['SAP_DB_NAME'],
    user=os.environ['SAP_DB_USER'],
    password=os.environ['SAP_DB_PASSWORD'],
    connect_timeout=5
)
print('OK:', conn.server_version)
conn.close()
"
```

### Auth service não responde

```powershell
docker compose exec backend python -c "
import urllib.request, os
try:
    r = urllib.request.urlopen(os.environ['AUTH_URL'] + '/api', timeout=5)
    print('Auth OK:', r.status)
except Exception as e:
    print('Erro:', e)
"
```

### Limpar imagens antigas (não apaga dados)

```powershell
docker image prune -f
```

---

## Referência rápida de variáveis do `.env`

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `ENVIRONMENT` | Sim | `production` — ativa as validações de segurança |
| `CP_DB_NAME` | Sim | Nome do banco interno do CP |
| `CP_DB_USER` | Sim | Usuário do banco interno |
| `CP_DB_PASSWORD` | Sim | Senha do banco interno |
| `CP_API_PORT` | Não | Porta da API (padrão: `3050`) |
| `FRONTEND_PORT` | Não | Porta do frontend (padrão: `5173`) |
| `CP_SECRET_KEY` | Sim | Gerado automaticamente pelo assistente |
| `SAP_DB_HOST` | Sim | IP ou hostname do servidor PostgreSQL SAP |
| `SAP_DB_PORT` | Não | Porta do banco SAP (padrão: `5432`) |
| `SAP_DB_NAME` | Sim | Nome do banco SAP |
| `SAP_DB_USER` | Sim | Usuário somente-leitura do banco SAP |
| `SAP_DB_PASSWORD` | Sim | Senha do usuário SAP |
| `JWT_SECRET` | Sim | Copiado do `config.env` do auth service |
| `AUTH_URL` | Sim | URL do serviço de autenticação (ex: `http://192.168.1.50:3001`) |
| `AUTH_ADMIN_USER` | Sim | Usuário admin do auth service |
| `AUTH_ADMIN_PASSWORD` | Sim | Senha admin do auth service |

> **`CP_DB_HOST` não entra no `.env`** — o Docker Compose injeta automaticamente o nome do serviço interno `cp_db`.
