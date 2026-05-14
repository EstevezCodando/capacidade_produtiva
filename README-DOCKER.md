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

## Resumo do fluxo (ordem obrigatória)

```
1. Instalar Docker Desktop
2. Baixar o projeto
3. Rodar setup.ps1  →  gera o .env com todas as credenciais
4. docker compose up -d --build  →  sobe o sistema
```

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

#### Como obter o JWT_SECRET

O `JWT_SECRET` está no arquivo `config.env` (ou `.env`) do serviço de autenticação,
na linha que começa com `JWT_SECRET=`. Peça ao responsável pelo auth service para
copiar esse valor e repassá-lo de forma segura antes de executar o setup.

---

## Passo 1 — Gerar o `.env` com o script de setup

Abra o PowerShell como Administrador, vá até a pasta do projeto e execute:

```powershell
cd C:\Sistemas\capacidade_produtiva
powershell -ExecutionPolicy Bypass -File setup.ps1
```

O script vai perguntar, na ordem:

1. **Banco CP** — nome, usuário e senha (você escolhe — o Docker cria o banco com esses dados)
2. **Banco SAP** — IP, porta, nome, usuário e senha do banco externo (somente leitura)
3. **Auth service** — URL, usuário e senha do administrador (o script testa a conexão e autentica)
4. **JWT_SECRET** — valor copiado do config.env do auth service

Ao final, o arquivo `.env` é criado automaticamente na pasta do projeto com encoding correto.

---

## Passo 2 — Subir o sistema

Com o `.env` pronto, suba todos os containers:

```powershell
docker compose up -d --build
```

Este comando:
1. Compila a imagem do backend (Python + dependências)
2. Compila a imagem do frontend (Node.js + Vite)
3. Sobe os três containers (`cp_db`, `backend`, `frontend`)
4. O backend executa as migrations Alembic automaticamente na primeira subida

O primeiro build demora de **3 a 10 minutos** dependendo da conexão com a internet.

---

## Passo 3 — Acompanhar a inicialização

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

## Passo 4 — Verificar status

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

---

## Passo 5 — Testar o sistema

```powershell
Invoke-WebRequest -Uri http://localhost:3050/api/health -UseBasicParsing
# StatusCode deve ser 200
```

Abra o navegador: **`http://localhost:5173`**

A tela de login deve aparecer. Use as credenciais do serviço de autenticação.

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

---

## Solução de problemas

### Porta 5433 bloqueada — `bind: An attempt was made to access a socket`

Ocorre quando o Windows reservou a porta para Hyper-V. Verifique:

```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```

Se a porta `5433` aparecer na lista, edite o `docker-compose.yml` e mude no serviço `cp_db`:

```yaml
ports:
  - "127.0.0.1:5434:5432"   # troque 5433 por qualquer porta livre
```

### Backend reiniciando em loop

```powershell
docker compose logs backend | Select-Object -Last 30
```

| Mensagem no log | Solução |
|-----------------|---------|
| `CP_SECRET_KEY deve ser definido em produção` | Rode `setup.ps1` novamente |
| `JWT_SECRET deve ser definido em produção` | Rode `setup.ps1` novamente |
| `AUTH_URL deve ser definido em produção` | Rode `setup.ps1` novamente |
| `could not connect to server` (SAP) | Verificar IP e firewall do banco SAP |
| `password authentication failed` | Usuário/senha errados no `.env` |
| `relation does not exist` | `docker compose exec backend python -m alembic upgrade head` |

### Login falha com "token inválido"

O `JWT_SECRET` no `.env` é diferente do auth service. Corrija:

```powershell
# Ver o valor atual
Select-String -Path .env -Pattern "JWT_SECRET"
```

Obtenha o valor correto com o responsável pelo auth service, edite o `.env` e reinicie:

```powershell
docker compose up -d
```

### Banco SAP não conecta

```powershell
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

### Limpar imagens antigas (não apaga dados)

```powershell
docker image prune -f
```

---

## Referência rápida de variáveis do `.env`

| Variável | Descrição |
|----------|-----------|
| `ENVIRONMENT` | `production` — ativa as validações de segurança |
| `CP_DB_NAME` | Nome do banco interno do CP |
| `CP_DB_USER` | Usuário do banco interno |
| `CP_DB_PASSWORD` | Senha do banco interno |
| `CP_API_PORT` | Porta da API (padrão: `3050`) |
| `FRONTEND_PORT` | Porta do frontend (padrão: `5173`) |
| `CP_SECRET_KEY` | Gerado automaticamente pelo `setup.ps1` |
| `SAP_DB_HOST` | IP ou hostname do servidor PostgreSQL SAP |
| `SAP_DB_PORT` | Porta do banco SAP (padrão: `5432`) |
| `SAP_DB_NAME` | Nome do banco SAP |
| `SAP_DB_USER` | Usuário somente-leitura do banco SAP |
| `SAP_DB_PASSWORD` | Senha do usuário SAP |
| `JWT_SECRET` | Copiado do `config.env` do auth service |
| `AUTH_URL` | URL do serviço de autenticação |
| `AUTH_ADMIN_USER` | Usuário admin do auth service |
| `AUTH_ADMIN_PASSWORD` | Senha admin do auth service |

> **`CP_DB_HOST` não entra no `.env`** — o Docker Compose injeta automaticamente o nome do serviço interno `cp_db`.
