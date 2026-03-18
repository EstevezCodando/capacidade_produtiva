// ============================================================
// API — funções tipadas para cada endpoint
// ============================================================
import type {
    InconsistenciasResponse,
    KpiDashboardResponse,
    KpiProjetosResponse,
    MeuDashboardResponse,
    SyncStatus,
    UsuarioMe,
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

export async function getKpiDashboard(): Promise<KpiDashboardResponse> {
  const res = await apiClient.get<KpiDashboardResponse>("/kpi/dashboard")
  return res.data
}

export async function getMeuDashboard(): Promise<MeuDashboardResponse> {
  const res = await apiClient.get<MeuDashboardResponse>("/kpi/meu-dashboard")
  return res.data
}
