# setup.ps1 - Configuracao inicial do Capacidade Produtiva
# Execute este script ANTES de rodar o Docker.
# Ele coleta as informacoes necessarias e gera o arquivo .env automaticamente.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

function Write-Ok   { param($msg) Write-Host "  OK  $msg" -ForegroundColor Cyan }
function Write-Err  { param($msg) Write-Host "ERRO  $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "" ; Write-Host "--- $msg ---" -ForegroundColor Yellow }

function Perguntar {
    param($pergunta, $default = $null, [switch]$senha)
    $prompt = if ($default) { "$pergunta [$default]" } else { $pergunta }
    while ($true) {
        if ($senha) {
            $secureVal = Read-Host "$prompt (oculto)" -AsSecureString
            $bstr  = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureVal)
            $valor = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        } else {
            $valor = Read-Host $prompt
        }
        if ($valor -eq "" -and $default -ne $null) { return $default }
        if ($valor -ne "") { return $valor }
        Write-Host "  Campo obrigatorio. Tente novamente." -ForegroundColor Red
    }
}

function Perguntar-SimNao {
    param($pergunta, $default = "s")
    $hint = if ($default -eq "s") { "S/n" } else { "s/N" }
    while ($true) {
        $valor = Read-Host "$pergunta ($hint)"
        if ($valor -eq "") { return ($default -eq "s") }
        if ($valor -match "^[sS]") { return $true }
        if ($valor -match "^[nN]") { return $false }
        Write-Host "  Digite s ou n." -ForegroundColor Red
    }
}

function Testar-Host {
    param($host_, $port_)
    $test = Test-NetConnection -ComputerName $host_ -Port ([int]$port_) -WarningAction SilentlyContinue
    return $test.TcpTestSucceeded
}

function Testar-Auth {
    param($url)
    try {
        $resp = Invoke-WebRequest -Uri "$url/api" -UseBasicParsing -TimeoutSec 5
        return $resp.StatusCode -eq 200
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
    $rng   = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $bytes = New-Object byte[] 48
    $rng.GetBytes($bytes)
    $rng.Dispose()
    return [System.Convert]::ToBase64String($bytes)
}

function Gerar-JwtSecret {
    $rng   = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $bytes = New-Object byte[] 64
    $rng.GetBytes($bytes)
    $rng.Dispose()
    return ([System.BitConverter]::ToString($bytes)).Replace("-", "").ToLower()
}

# =============================================================================
# Inicio
# =============================================================================

Clear-Host
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Capacidade Produtiva - Configuracao inicial"             -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Este script coleta as informacoes necessarias e gera"
Write-Host "o arquivo .env para voce executar o Docker em seguida."
Write-Host ""

if (Test-Path ".env") {
    $resp = Read-Host ".env ja existe. Deseja sobrescrever? (s/N)"
    if ($resp -notmatch "^[sS]") {
        Write-Host "Cancelado." -ForegroundColor Yellow
        exit 0
    }
}

# =============================================================================
# Banco CP — interno (Docker) ou externo (servidor existente)?
# =============================================================================

Write-Step "Banco de dados do Capacidade Produtiva"
Write-Host ""
Write-Host "  Opcoes:"
Write-Host "    1 - Criar banco interno (gerenciado pelo Docker, recomendado para nova instalacao)"
Write-Host "    2 - Usar banco externo ja existente (outro servidor PostgreSQL)"
Write-Host ""

$cpOpcao = ""
while ($cpOpcao -ne "1" -and $cpOpcao -ne "2") {
    $cpOpcao = Read-Host "  Escolha [1/2]"
    if ($cpOpcao -eq "") { $cpOpcao = "1" }
}

$cpDbHost         = ""
$cpDbPort         = "5432"
$cpDbName         = ""
$cpDbUser         = ""
$cpDbPassword     = ""
$composeProfiles  = ""

if ($cpOpcao -eq "1") {
    # Banco interno — Docker sobe o cp_db automaticamente
    Write-Host ""
    Write-Host "  O Docker vai criar e gerenciar o banco automaticamente."
    Write-Host "  Escolha um nome de usuario e senha para ele."
    Write-Host ""

    $cpDbName     = Perguntar "Nome do banco" "capacidade_produtiva"
    $cpDbUser     = Perguntar "Usuario do banco" "cp_user"
    $cpDbPassword = Perguntar "Senha do banco (escolha uma senha forte)" -senha

    $cpDbHost        = "cp_db"   # nome do servico Docker interno
    $cpDbPort        = "5432"
    $composeProfiles = "local-db"

    Write-Ok "Banco interno configurado (Docker ira criar o PostgreSQL)"

} else {
    # Banco externo — usuario informa o servidor existente
    Write-Host ""
    Write-Host "  Informe os dados de conexao do PostgreSQL existente."
    Write-Host ""

    $cpDbHost     = Perguntar "IP ou hostname do servidor PostgreSQL do CP"
    $cpDbPort     = Perguntar "Porta do PostgreSQL do CP" "5432"
    $cpDbName     = Perguntar "Nome do banco de dados do CP" "capacidade_produtiva"
    $cpDbUser     = Perguntar "Usuario do banco do CP"
    $cpDbPassword = Perguntar "Senha do usuario" -senha

    Write-Host ""
    Write-Host "  Testando conexao com ${cpDbHost}:${cpDbPort}..." -NoNewline
    if (Testar-Host $cpDbHost $cpDbPort) {
        Write-Ok "Banco CP acessivel"
    } else {
        Write-Host ""
        Write-Host "  AVISO: Nao foi possivel conectar em ${cpDbHost}:${cpDbPort}" -ForegroundColor Yellow
        Write-Host "  Verifique o firewall/IP. O setup continuara mesmo assim."    -ForegroundColor Yellow
    }

    $composeProfiles = ""   # cp_db nao sobe no Docker

    Write-Ok "Banco externo configurado"
}

# =============================================================================
# Portas da API e frontend
# =============================================================================

Write-Host ""
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
$sapDbPassword = Perguntar "Senha do usuario SAP" -senha

Write-Host ""
Write-Host "  Testando conexao com o banco SAP..." -NoNewline
if (Testar-Host $sapDbHost $sapDbPort) {
    Write-Ok "Banco SAP acessivel"
} else {
    Write-Host ""
    Write-Host "  AVISO: Nao foi possivel conectar em ${sapDbHost}:${sapDbPort}" -ForegroundColor Yellow
    Write-Host "  Verifique o firewall. O setup continuara mesmo assim."         -ForegroundColor Yellow
}

# =============================================================================
# Servico de Autenticacao
# =============================================================================

Write-Step "Servico de Autenticacao"

while ($true) {
    $authUrl = Perguntar "URL do servico de autenticacao (ex: http://192.168.1.50:3001)"
    $authUrl = $authUrl.TrimEnd("/")

    Write-Host "  Testando conexao..." -NoNewline
    if (Testar-Auth $authUrl) {
        Write-Ok "Servico de autenticacao operacional"
        break
    } else {
        Write-Err "Nao foi possivel conectar em $authUrl"
        Write-Host "  Verifique o endereco e tente novamente." -ForegroundColor Yellow
    }
}

$authAdminUser     = Perguntar "Usuario administrador do auth service"
$authAdminPassword = Perguntar "Senha do administrador" -senha

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
# Gerar chaves automaticamente
# =============================================================================

Write-Host ""
Write-Host "  Gerando chaves de seguranca automaticamente..." -NoNewline
$cpSecretKey = Gerar-SecretKey
$jwtSecret   = Gerar-JwtSecret
Write-Ok "Chaves geradas"

# =============================================================================
# Gravar .env em UTF-8 sem BOM
# =============================================================================

$envContent = "ENVIRONMENT=production`r`n"
$envContent += "`r`n"
$envContent += "# Banco CP`r`n"
$envContent += "CP_DB_HOST=$cpDbHost`r`n"
$envContent += "CP_DB_PORT=$cpDbPort`r`n"
$envContent += "CP_DB_NAME=$cpDbName`r`n"
$envContent += "CP_DB_USER=$cpDbUser`r`n"
$envContent += "CP_DB_PASSWORD=$cpDbPassword`r`n"
$envContent += "`r`n"
$envContent += "CP_API_PORT=$cpApiPort`r`n"
$envContent += "FRONTEND_PORT=$frontendPort`r`n"
$envContent += "`r`n"
$envContent += "CP_SECRET_KEY=$cpSecretKey`r`n"
$envContent += "`r`n"
$envContent += "# Banco SAP`r`n"
$envContent += "SAP_DB_HOST=$sapDbHost`r`n"
$envContent += "SAP_DB_PORT=$sapDbPort`r`n"
$envContent += "SAP_DB_NAME=$sapDbName`r`n"
$envContent += "SAP_DB_USER=$sapDbUser`r`n"
$envContent += "SAP_DB_PASSWORD=$sapDbPassword`r`n"
$envContent += "`r`n"
$envContent += "JWT_SECRET=$jwtSecret`r`n"
$envContent += "AUTH_URL=$authUrl`r`n"
$envContent += "AUTH_ADMIN_USER=$authAdminUser`r`n"
$envContent += "AUTH_ADMIN_PASSWORD=$authAdminPassword`r`n"
$envContent += "`r`n"
$envContent += "# Perfil Docker: local-db = sobe o cp_db interno; vazio = banco externo`r`n"
$envContent += "COMPOSE_PROFILES=$composeProfiles`r`n"

[System.IO.File]::WriteAllText(
    "$PWD\.env",
    $envContent,
    [System.Text.UTF8Encoding]::new($false)
)

# =============================================================================
# Conclusao
# =============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Configuracao concluida! Arquivo .env gerado."             -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

if ($cpOpcao -eq "1") {
    Write-Host "  Banco CP: interno (Docker vai criar o PostgreSQL automaticamente)"
} else {
    Write-Host "  Banco CP: externo em ${cpDbHost}:${cpDbPort}"
}

Write-Host ""
Write-Host "Proximo passo - subir o sistema:"
Write-Host ""
Write-Host "   docker compose up -d --build"
Write-Host ""
Write-Host "Acompanhe a inicializacao com:"
Write-Host ""
Write-Host "   docker compose logs -f backend"
Write-Host ""
