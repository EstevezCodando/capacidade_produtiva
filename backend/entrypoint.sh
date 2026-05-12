#!/bin/sh
# =============================================================================
# entrypoint.sh — Pipeline de inicialização do backend CapacidadeProdutiva
#
# Ordem:
#   1. Migrações Alembic  — falha crítica: banco deve estar ok
#   2. Sincronização SAP  — falha suave: API sobe mesmo sem dados SAP frescos
#   3. Uvicorn            — processo principal (exec substitui este shell)
# =============================================================================
set -e

PORTA="${CP_API_PORT:-3050}"

# ── helpers ──────────────────────────────────────────────────────────────────

banner() {
  echo ""
  echo "══════════════════════════════════════════════════════════════"
  printf "  ► %s\n" "$1"
  echo "══════════════════════════════════════════════════════════════"
}

erro_critico() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║  ERRO CRÍTICO — CapacidadeProdutiva não pôde inicializar    ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  printf "  Etapa falhou : %s\n" "$1"
  echo "  Verifique os logs acima e as variáveis de ambiente (.env)."
  echo ""
  exit 1
}

# ── 1. Migrações ──────────────────────────────────────────────────────────────

banner "Migrações Alembic (upgrade head)"
alembic upgrade head || erro_critico "alembic upgrade head"

# ── 2. Sincronização SAP ──────────────────────────────────────────────────────

banner "Sincronização SAP → sap_snapshot"
if sincronizar-sap; then
  echo "  ✔ Sincronização SAP concluída."
else
  echo ""
  echo "  ⚠  Sincronização SAP falhou — API será iniciada com dados existentes."
  echo "  Verifique as variáveis SAP_DB_* e a conectividade com o banco SAP."
fi

# ── 3. API ────────────────────────────────────────────────────────────────────

banner "API CapacidadeProdutiva  →  http://0.0.0.0:${PORTA}"
echo "  Variáveis de ambiente detectadas:"
echo "    CP_API_PORT  = ${PORTA}"
echo "    ENVIRONMENT  = ${ENVIRONMENT:-production}"
echo "    CP_DB_HOST   = ${CP_DB_HOST:-<não definido>}"
echo ""

# exec substitui o processo shell pelo uvicorn — sinais (SIGTERM) chegam direto
exec uvicorn cp.main:app \
  --host 0.0.0.0 \
  --port "${PORTA}" \
  --log-level info \
  --access-log
