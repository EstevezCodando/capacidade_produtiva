// ============================================================
// API — funções tipadas para cada endpoint
// ============================================================
import type {
    InconsistenciasResponse,
    KpiProjetosResponse,
    SyncStatus,
    UsuarioMe,
} from "@/types";
import { apiClient } from "./client";

// ── Auth ─────────────────────────────────────────────────────
// O login é feito contra o servico_autenticacao externo.
// O frontend envia as credenciais para o auth e recebe o JWT,
// depois usa o JWT para chamar /api/usuarios/me para obter o perfil.
export async function loginAuth(
  authUrl: string,
  username: string,
  password: string,
): Promise<string> {
  // O servico_autenticacao pode variar — aqui assumimos POST /login → { token }
  const res = await fetch(`${authUrl}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Credenciais inválidas");
  const data = (await res.json()) as { token?: string; access_token?: string };
  return data.token ?? data.access_token ?? "";
}

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

export const getKpiDashboard = async () => {
  // Ajuste "api" para o nome da sua instância do axios, se for diferente
  const res = await apiClient.get("/kpi/dashboard");
  return res.data;
};
