// ============================================================
// API — funções tipadas para cada endpoint
// ============================================================
import type {
    InconsistenciasResponse,
    KpiDashboardResponse,
    KpiProjetosResponse,
    MeuDashboardResponse,
    PizzaDistribuicaoResponse,
    SyncStatus,
    UsuarioMe,
    UsuarioResumo,
} from "@/types";
import { apiClient } from "./client";

export async function getUsuarioMe(): Promise<UsuarioMe> {
  const res = await apiClient.get<UsuarioMe>("/usuarios/me");
  return res.data;
}

// ── Sync ─────────────────────────────────────────────────────
export async function getSyncStatus(): Promise<SyncStatus> {
  const res = await apiClient.get<SyncStatus>("/sync/status");
  return res.data;
}

export async function executarSync(): Promise<{ detail: string }> {
  const res = await apiClient.post<{ detail: string }>("/sync/executar");
  return res.data;
}

// ── KPI ──────────────────────────────────────────────────────
export async function getKpiProjetos(): Promise<KpiProjetosResponse> {
  const res = await apiClient.get<KpiProjetosResponse>("/kpi/projetos");
  return res.data;
}

export async function getInconsistencias(): Promise<InconsistenciasResponse> {
  const res = await apiClient.get<InconsistenciasResponse>(
    "/kpi/inconsistencias",
  );
  return res.data;
}

// ── Health ────────────────────────────────────────────────────
export async function getHealth(): Promise<{ status: string }> {
  const res = await apiClient.get<{ status: string }>("/health");
  return res.data;
}

export async function getKpiDashboard(blocoId?: number, subfaseId?: number): Promise<KpiDashboardResponse> {
  const params: Record<string, number> = {}
  if (blocoId)   params.bloco_id   = blocoId
  if (subfaseId) params.subfase_id = subfaseId
  const res = await apiClient.get<KpiDashboardResponse>("/kpi/dashboard", {
    params: Object.keys(params).length ? params : undefined,
  })
  return res.data
}

export async function getMeuDashboard(): Promise<MeuDashboardResponse> {
  const res = await apiClient.get<MeuDashboardResponse>("/kpi/meu-dashboard")
  return res.data
}

export async function getMinhaPizzaMensal(mes: string): Promise<PizzaDistribuicaoResponse> {
  const res = await apiClient.get<PizzaDistribuicaoResponse>("/kpi/minha-distribuicao", { params: { mes } })
  return res.data
}

export async function getPizzaMensal(mes: string, usuarioId = 0): Promise<PizzaDistribuicaoResponse> {
  const res = await apiClient.get<PizzaDistribuicaoResponse>("/kpi/distribuicao-mensal", {
    params: { mes, usuario_id: usuarioId },
  })
  return res.data
}

export async function getUsuarios(): Promise<UsuarioResumo[]> {
  const res = await apiClient.get<UsuarioResumo[]>("/usuarios")
  return res.data
}
