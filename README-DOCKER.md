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

Clone ou copie o projeto para o servidor. Exemplo:

```powershell
# Via git
git clone <url-do-repositorio> C:\Sistemas\capacidade_produtiva
cd C:\Sistemas\capacidade_produtiva

# Ou extraia o ZIP diretamente em C:\Sistemas\capacidade_produtiva
```

### 3. Informações necessárias antes de começar

Tenha em mãos antes de prosseguir:

| Dado | Onde obter |
|------|-----------|
| IP/hostname do servidor SAP | Equipe de infraestrutura |
| Porta do PostgreSQL SAP | Padrão: 5432 |
| Nome do banco SAP | Equipe SAP |
| Usuário e senha (somente-leitura) do banco SAP | DBA / equipe SAP |
| URL do serviço de autenticação | Ex: `http://192.168.1.50:3001` |
| Usuário e senha admin do serviço de autenticação | Responsável pelo auth service |
| JWT_SECRET do serviço de autenticação | **Deve ser idêntico** ao configurado no auth service |

---

## Passo 1 — Abrir o PowerShell como Administrador

Clique em Iniciar → pesquise "PowerShell" → botão direito → **Executar como administrador**.

```powershell
cd C:\Sistemas\capacidade_produtiva
```

---

## Passo 2 — Gerar as chaves secretas

O sistema precisa de duas chaves criptográficas. Gere-as agora e anote os valores — eles não podem mudar após o primeiro start sem invalidar todas as sessões ativas.

```powershell
# CP_SECRET_KEY — chave interna do sistema (sessões, CSRF)
Write-Host "CP_SECRET_KEY:"
[System.Convert]::ToBase64String(
    [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48)
)

Write-Host ""

# JWT_SECRET — deve ser IDÊNTICO ao configurado no serviço de autenticação
# Se o auth service já está rodando, use a chave que está configurada lá.
# Só gere uma nova se for configurar o auth service ao mesmo tempo.
Write-Host "JWT_SECRET (use o mesmo do auth service se ele já existe):"
[System.Convert]::ToBase64String(
    [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(64)
)
```

Copie os dois valores gerados para um local seguro.

> **Atenção:** `JWT_SECRET` deve ser exatamente igual ao `JWT_SECRET` configurado no serviço de autenticação SAP. Se os valores divergirem, o login não vai funcionar.

---

## Passo 3 — Criar o arquivo `.env`

```powershell
# Copiar o arquivo de exemplo
Copy-Item .env.example .env

# Abrir para edição
notepad .env
```

Preencha **todos** os campos com seus valores reais:

```env
ENVIRONMENT=production

# ── Banco do CP (gerenciado pelo Docker — não altere CP_DB_HOST) ───────────
# CP_DB_HOST não vai aqui: o Compose injeta "cp_db" automaticamente.
CP_DB_NAME=capacidade_produtiva
CP_DB_USER=cp_user
CP_DB_PASSWORD=DEFINA_UMA_SENHA_FORTE_AQUI

# ── Portas expostas na máquina ─────────────────────────────────────────────
CP_API_PORT=3050
FRONTEND_PORT=5173

# ── Chave interna do CP (gerada no Passo 2) ────────────────────────────────
CP_SECRET_KEY=COLE_AQUI_O_VALOR_GERADO_PARA_CP_SECRET_KEY

# ── Banco SAP externo (somente leitura) ────────────────────────────────────
SAP_DB_HOST=192.168.1.100        # IP ou hostname do servidor SAP
SAP_DB_PORT=5432
SAP_DB_NAME=nome_do_banco_sap
SAP_DB_USER=usuario_readonly_sap
SAP_DB_PASSWORD=senha_do_usuario_sap

# ── Autenticação (serviço em outra máquina) ────────────────────────────────
JWT_SECRET=COLE_AQUI_O_JWT_SECRET_DO_AUTH_SERVICE
AUTH_URL=http://192.168.1.50:3001   # URL do serviço de autenticação
AUTH_ADMIN_USER=usuario_admin
AUTH_ADMIN_PASSWORD=senha_admin
```

Salve com **Arquivo → Salvar** (não "Salvar como") e feche o Bloco de Notas.

### Regras obrigatórias do arquivo `.env`

- Sem espaços ao redor do `=` (use `CHAVE=valor`, não `CHAVE = valor`)
- Sem comentários na mesma linha do valor
- Valores com espaços precisam de aspas: `DESCRICAO="Sistema CP"`
- Não commite este arquivo no git (já está no `.gitignore`)

---

## Passo 4 — Corrigir encoding do `.env` (obrigatório)

O Bloco de Notas do Windows salva com BOM (Byte Order Mark) que o Docker não lê corretamente. Corrija com:

```powershell
$content = Get-Content .env -Raw
[System.IO.File]::WriteAllText(
    "$PWD\.env",
    $content,
    [System.Text.UTF8Encoding]::new($false)
)
```

---

## Passo 5 — Verificar se o `.env` está sendo lido

```powershell
docker compose config | Select-String -Pattern "CP_DB|SAP_DB|JWT|AUTH|CP_SECRET"
```

Todas as variáveis devem aparecer com seus valores preenchidos (não em branco). Se alguma aparecer vazia, revise o passo 3 e 4.

---

## Passo 6 — Verificar conectividade com os serviços externos

Antes de subir os containers, confirme que o servidor pode alcançar o banco SAP e o auth service:

```powershell
# Testar conexão com o banco SAP
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432

# Testar conexão com o serviço de autenticação
Test-NetConnection -ComputerName 192.168.1.50 -Port 3001
```

A coluna `TcpTestSucceeded` deve retornar `True`. Se retornar `False`, verifique:
- Firewall do servidor de destino (liberar a porta para o IP deste servidor)
- Firewall do Windows Server local (saída nas portas)
- Credenciais de VPN ou rede, se necessário

---

## Passo 7 — Build e primeira subida

```powershell
docker compose --env-file .env up -d --build
```

Este comando:
1. Compila a imagem do backend (Python + dependências)
2. Compila a imagem do frontend (Node.js + Vite build)
3. Sobe os três containers (`cp_db`, `backend`, `frontend`)

O primeiro build demora de 3 a 10 minutos dependendo da velocidade da máquina e da conexão com a internet.

---

## Passo 8 — Acompanhar a inicialização

```powershell
# Ver logs de todos os serviços em tempo real
docker compose logs -f

# Ou somente o backend (onde migrations e sync SAP rodam)
docker compose logs -f backend
```

A sequência normal de inicialização do backend é:

```
backend  | Running Alembic migrations...
backend  | INFO  [alembic.runtime.migration] Running upgrade ...
backend  | Migrations complete.
backend  | Running SAP sync...
backend  | SAP sync complete.
backend  | INFO:     Application startup complete.
backend  | INFO:     Uvicorn running on http://0.0.0.0:3050
```

Pressione `Ctrl+C` para sair dos logs sem parar os containers.

---

## Passo 9 — Verificar status dos containers

```powershell
docker compose ps
```

Todos devem estar `running` ou `healthy`:

```
NAME         STATUS
cp_db        running (healthy)
backend      running (healthy)
frontend     running (healthy)
```

Se algum mostrar `restarting`, ele está com erro. Veja os logs:

```powershell
docker compose logs backend
```

---

## Passo 10 — Executar as migrations manualmente (se necessário)

As migrations rodam automaticamente no start, mas caso precise executar manualmente:

```powershell
docker compose exec backend python -m alembic upgrade head
```

Para verificar o estado atual das migrations:

```powershell
docker compose exec backend python -m alembic current
```

---

## Passo 11 — Testar o sistema

```powershell
# Testar o endpoint de saúde da API
Invoke-WebRequest -Uri http://localhost:3050/api/health -UseBasicParsing

# Deve retornar StatusCode 200
```

Abra o navegador e acesse: `http://localhost:5173`

A tela de login deve aparecer. Use as credenciais do serviço de autenticação para entrar.

---

## Operações do dia a dia

### Parar os containers

```powershell
docker compose down
```

Os dados do banco ficam preservados no volume `cp_db_data`.

### Reiniciar os containers

```powershell
docker compose up -d
```

### Ver logs

```powershell
docker compose logs -f backend        # backend em tempo real
docker compose logs --tail=100 backend # últimas 100 linhas
```

### Atualizar após nova versão do código

```powershell
# 1. Baixar nova versão (git)
git pull

# 2. Rebuild das imagens
docker compose build

# 3. Recriar containers com nova imagem
docker compose up -d

# 4. As migrations rodam automaticamente no start
#    Para confirmar:
docker compose logs backend | Select-String "alembic"
```

### Executar sincronização SAP manualmente

```powershell
docker compose exec backend sincronizar-sap
```

---

## Solução de problemas

### Variáveis do `.env` aparecem em branco no `docker compose config`

```powershell
# Verificar se o arquivo tem extensão oculta (.env.txt)
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

Causas comuns:

| Mensagem no log | Solução |
|-----------------|---------|
| `CP_SECRET_KEY deve ser definido em produção` | Preencher `CP_SECRET_KEY` no `.env` |
| `JWT_SECRET deve ser definido em produção` | Preencher `JWT_SECRET` no `.env` |
| `AUTH_URL deve ser definido em produção` | Preencher `AUTH_URL` no `.env` |
| `could not connect to server` (banco SAP) | Verificar `SAP_DB_HOST`, porta e firewall |
| `password authentication failed` | Verificar usuário/senha do banco |
| `relation does not exist` | Rodar `docker compose exec backend python -m alembic upgrade head` |

### Banco SAP não conecta

```powershell
# Testar conectividade de rede
Test-NetConnection -ComputerName $env:SAP_DB_HOST -Port 5432

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
print('Conexão OK:', conn.server_version)
conn.close()
"
```

### Auth service não responde

```powershell
# Testar de dentro do container
docker compose exec backend python -c "
import urllib.request, os
url = os.environ['AUTH_URL'] + '/health'
try:
    r = urllib.request.urlopen(url, timeout=5)
    print('Auth OK:', r.status)
except Exception as e:
    print('Erro:', e)
"
```

### Frontend mostra tela em branco ou erro 502

O nginx faz proxy de `/api` para o backend. Se o backend ainda não está `healthy`, o frontend não sobe. Aguarde o backend ficar saudável:

```powershell
# Monitorar até ficarem healthy
docker compose ps
```

### Verificar uso de disco (volumes)

```powershell
docker system df
docker volume ls
```

Para limpar imagens antigas não usadas (não apaga dados):

```powershell
docker image prune -f
```

---

## Referência rápida de variáveis do `.env`

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `ENVIRONMENT` | Sim | `production` (qualquer outro valor desativa validações de segurança) |
| `CP_DB_NAME` | Sim | Nome do banco interno do CP |
| `CP_DB_USER` | Sim | Usuário do banco interno |
| `CP_DB_PASSWORD` | Sim | Senha do banco interno |
| `CP_API_PORT` | Não | Porta da API (padrão: 3050) |
| `FRONTEND_PORT` | Não | Porta do frontend (padrão: 5173) |
| `CP_SECRET_KEY` | Sim | Chave interna para sessões (gerar no Passo 2) |
| `SAP_DB_HOST` | Sim | IP ou hostname do servidor PostgreSQL SAP |
| `SAP_DB_PORT` | Não | Porta do banco SAP (padrão: 5432) |
| `SAP_DB_NAME` | Sim | Nome do banco SAP |
| `SAP_DB_USER` | Sim | Usuário somente-leitura do banco SAP |
| `SAP_DB_PASSWORD` | Sim | Senha do usuário SAP |
| `JWT_SECRET` | Sim | **Deve ser idêntico** ao JWT_SECRET do auth service |
| `AUTH_URL` | Sim | URL base do serviço de autenticação (ex: `http://192.168.1.50:3001`) |
| `AUTH_ADMIN_USER` | Sim | Usuário admin do auth service |
| `AUTH_ADMIN_PASSWORD` | Sim | Senha admin do auth service |

> **`CP_DB_HOST` não entra no `.env`** — o Compose injeta automaticamente o nome do serviço interno `cp_db`.
