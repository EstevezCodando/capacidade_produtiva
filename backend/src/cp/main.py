# Ponto de entrada do sistema.
# Sprint 1: FastAPI mínimo — apenas garante que o servidor sobe.
# Sprints futuros adicionarão routers, middleware e configuração real.

from fastapi import FastAPI

app = FastAPI(
    title="CapacidadeProdutiva",
    description="Sistema de gestão operacional que une produção (SAP) e capacidade (agenda).",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check — confirma que o servidor está no ar."""
    return {"status": "ok"}
