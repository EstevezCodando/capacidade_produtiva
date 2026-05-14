# setup.ps1 — Configuração inicial do Capacidade Produtiva
# Execute este script ANTES de rodar o Docker.
# Ele coleta as informações necessárias e gera o arquivo .env automaticamente.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

function Write-Ok   { param($msg) Write-Host "  OK  $msg" -ForegroundColor Cyan }
function Write-Err  { param($msg) Write-Host "ERRO  $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "`n--- $msg ---" -ForegroundColor Yellow }

function Perguntar {
    param($pergunta, $default = $null, $senha = $false)
    $prompt = if ($default) { "$pergunta [$default]" } else { $pergunta }
    while ($true) {
        if ($senha) {
            $valor = Read-Host "$prompt (oculto)"
        } else {
            $valor = Read-Host $prompt
        }
        if ($valor -eq "" -and $default -ne $null) { return $default }
        if ($valor -ne "") { return $valor }
        Write-Host "  Campo obrigatorio. Tente novamente." -ForegroundColor Red
    }
}

function Testar-Auth {
    param($url)
    try {
        $resp = Invoke-WebRequest -Uri "$url/api" -UseBasicParsing -TimeoutSec 5
        $json = $resp.Content | ConvertFrom-Json
        return $json.message -eq "Servico de autenticacao operacional" -or $resp.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Autenticar {
    param($url, $usuario, $senha)
    try {
        $body = @{ usuario = $usuario; senha = $senha; aplicacao = "sap" } | ConvertTo-Json
        $resp = Invoke-WebRequest -Uri "$url/api/login" `
            -Method Post `
            -Body $body `
            -ContentType "application/json" `
            -UseBasicParsing `
            -TimeoutSec 10
        $json = $resp.Content | ConvertFrom-Json
        if ($json.success) { return $json.dados.token }
        throw "Credenciais invalidas"
    } catch {
        throw "Falha ao autenticar: $_"
    }
}

function Gerar-SecretKey {
    $bytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48)
    return [System.Convert]::ToBase64String($bytes)
}

# =============================================================================
# Inicio
# =============================================================================

Clear-Host
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Capacidade Produtiva — Configuracao inicial" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Este script vai coletar as informacoes necessarias e gerar"
Write-Host "o arquivo .env para voce executar o Docker em seguida."
Write-Host ""

# Verificar se .env ja existe
if (Test-Path ".env") {
    $resp = Read-Host ".env ja existe. Deseja sobrescrever? (s/N)"
    if ($resp -notmatch "^[sS]") {
        Write-Host "Cancelado." -ForegroundColor Yellow
        exit 0
    }
}

# =============================================================================
# Banco CP (interno — gerenciado pelo Docker)
# =============================================================================

Write-Step "Banco de dados do Capacidade Produtiva (interno)"
Write-Host "  Este banco sera criado automaticamente pelo Docker."
Write-Host "  Escolha um usuario e senha para ele."
Write-Host ""

$cpDbName     = Perguntar "Nome do banco" "capacidade_produtiva"
$cpDbUser     = Perguntar "Usuario do banco" "cp_user"
$cpDbPassword = Perguntar "Senha do banco (escolha uma senha forte)" -senha $true
$cpApiPort    = Perguntar "Porta da API" "3050"
$frontendPort = Perguntar "Porta do frontend" "5173"

# =============================================================================
# Banco SAP (externo, somente leitura)
# =============================================================================

Write-Step "Banco de dados SAP (externo, somente leitura)"

$sapDbHost     = Perguntar "IP ou hostname do servidor SAP"
$sapDbPort     = Perguntar "Porta do PostgreSQL SAP" "5432"
$sapDbName     = Perguntar "Nome do banco SAP"
$sapDbUser     = Perguntar "Usuario somente-leitura do banco SAP"
$sapDbPassword = Perguntar "Senha do usuario SAP" -senha $true

Write-Host ""
Write-Host "  Testando conexao com o banco SAP..." -NoNewline
$sapTest = Test-NetConnection -ComputerName $sapDbHost -Port ([int]$sapDbPort) -WarningAction SilentlyContinue
if ($sapTest.TcpTestSucceeded) {
    Write-Ok "Banco SAP acessivel"
} else {
    Write-Host ""
    Write-Host "  AVISO: Nao foi possivel conectar em $sapDbHost`:$sapDbPort" -ForegroundColor Yellow
    Write-Host "  Verifique o firewall. O setup continuara mesmo assim." -ForegroundColor Yellow
}

# =============================================================================
# Servico de Autenticacao
# =============================================================================

Write-Step "Servico de Autenticacao"

while ($true) {
    $authUrl = Perguntar "URL do servico de autenticacao (ex: http://192.168.1.50:3001)"
    $authUrl  = $authUrl.TrimEnd("/")

    Write-Host "  Testando conexao..." -NoNewline
    if (Testar-Auth $authUrl) {
        Write-Ok "Servico de autenticacao operacional"
        break
    } else {
        Write-Err "Nao foi possivel conectar em $authUrl"
        Write-Host "  Verifique o endereco e tente novamente." -ForegroundColor Yellow
    }
}

$authAdminUser = Perguntar "Usuario administrador do auth service"
$authAdminPassword = Perguntar "Senha do administrador" -senha $true

Write-Host "  Autenticando..." -NoNewline
try {
    $token = Autenticar $authUrl $authAdminUser $authAdminPassword
    Write-Ok "Login realizado com sucesso"
} catch {
    Write-Err "Falha na autenticacao: $_"
    Write-Host "  Verifique o usuario e senha e execute o script novamente." -ForegroundColor Yellow
    exit 1
}

# =============================================================================
# JWT_SECRET
# =============================================================================

Write-Step "Chave JWT (JWT_SECRET)"
Write-Host ""
Write-Host "  O JWT_SECRET deve ser IDENTICO ao configurado no servico de"
Write-Host "  autenticacao. Ele esta no arquivo config.env (ou .env) do"
Write-Host "  auth service, na linha que comeca com:  JWT_SECRET="
Write-Host ""

$jwtSecret = Perguntar "JWT_SECRET do servico de autenticacao" -senha $true
if ($jwtSecret -eq "") {
    Write-Err "JWT_SECRET nao pode ser vazio."
    exit 1
}

# =============================================================================
# Gerar CP_SECRET_KEY automaticamente
# =============================================================================

Write-Host ""
Write-Host "  Gerando CP_SECRET_KEY automaticamente..." -NoNewline
$cpSecretKey = Gerar-SecretKey
Write-Ok "CP_SECRET_KEY gerado"

# =============================================================================
# Gravar .env
# =============================================================================

$envContent = @"
ENVIRONMENT=production

# Banco do CP (interno — gerenciado pelo Docker)
CP_DB_NAME=$cpDbName
CP_DB_USER=$cpDbUser
CP_DB_PASSWORD=$cpDbPassword

# Portas expostas
CP_API_PORT=$cpApiPort
FRONTEND_PORT=$frontendPort

# Chave interna do CP (gerada automaticamente)
CP_SECRET_KEY=$cpSecretKey

# Banco SAP (externo, somente leitura)
SAP_DB_HOST=$sapDbHost
SAP_DB_PORT=$sapDbPort
SAP_DB_NAME=$sapDbName
SAP_DB_USER=$sapDbUser
SAP_DB_PASSWORD=$sapDbPassword

# Servico de Autenticacao
JWT_SECRET=$jwtSecret
AUTH_URL=$authUrl
AUTH_ADMIN_USER=$authAdminUser
AUTH_ADMIN_PASSWORD=$authAdminPassword
"@

# Gravar em UTF-8 sem BOM (obrigatorio para o Docker Compose ler corretamente)
[System.IO.File]::WriteAllText("$PWD\.env", $envContent, [System.Text.UTF8Encoding]::new($false))

# =============================================================================
# Conclusao
# =============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Configuracao concluida! Arquivo .env gerado." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Proximo passo — subir o sistema:"
Write-Host ""
Write-Host "   docker compose up -d --build" -ForegroundColor White
Write-Host ""
Write-Host "Acompanhe a inicializacao com:"
Write-Host ""
Write-Host "   docker compose logs -f backend" -ForegroundColor White
Write-Host ""
