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

A seguir, uma simulação com dados de exemplo mostrando exatamente o que aparece na tela em cada etapa.

> **Dados usados no exemplo:**
> - Banco SAP: `192.168.10.50:5432` / banco `sap_producao` / usuário `cp_readonly`
> - Auth service: `http://192.168.10.30:3001` / admin `joao.silva`

---

### PASSO 1 — Abrir o PowerShell como Administrador

Clique em **Iniciar** → pesquise **PowerShell** → botão direito → **Executar como administrador**.

```
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\Windows\System32>
```

Navegue até a pasta do projeto:

```powershell
PS C:\Windows\System32> cd C:\Sistemas\capacidade_produtiva
PS C:\Sistemas\capacidade_produtiva>
```

---

### PASSO 2 — Executar o script de setup

```powershell
PS C:\Sistemas\capacidade_produtiva> powershell -ExecutionPolicy Bypass -File setup.ps1
```

O script pergunta tudo interativamente. Pressione **Enter** para aceitar o valor padrão entre colchetes `[ ]`.

```
============================================================
   Capacidade Produtiva — Configuracao inicial
============================================================

Este script vai coletar as informacoes necessarias e gerar
o arquivo .env para voce executar o Docker em seguida.


--- Banco de dados do Capacidade Produtiva (interno) ---
  Este banco sera criado automaticamente pelo Docker.
  Escolha um usuario e senha para ele.

Nome do banco [capacidade_produtiva]: ↵
Usuario do banco [cp_user]: ↵
Senha do banco (escolha uma senha forte) (oculto): ************
Porta da API [3050]: ↵
Porta do frontend [5173]: ↵


--- Banco de dados SAP (externo, somente leitura) ---

IP ou hostname do servidor SAP: 192.168.10.50
Porta do PostgreSQL SAP [5432]: ↵
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

Proximo passo — subir o sistema:

   docker compose up -d --build

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
| `JWT_SECRET` | Gerado automaticamente pelo `setup.ps1` |
| `AUTH_URL` | URL do serviço de autenticação |
| `AUTH_ADMIN_USER` | Usuário admin do auth service |
| `AUTH_ADMIN_PASSWORD` | Senha admin do auth service |

> **`CP_DB_HOST` não entra no `.env`** — o Docker Compose injeta automaticamente o nome do serviço interno `cp_db`.
