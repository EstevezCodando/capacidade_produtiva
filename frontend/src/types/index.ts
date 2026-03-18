// ============================================================
// CapacidadeProdutiva — Shared Types
// Mirrors backend Pydantic schemas exactly
// ============================================================

// ── Auth / Usuário ───────────────────────────────────────────
export interface UsuarioMe {
  usuario_id:    number
  usuario_uuid:  string
  nome:          string
  nome_guerra:   string | null
  administrador: boolean
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthToken {
  token: string
}

// ── Sessão local ─────────────────────────────────────────────
export interface SessaoLocal {
  token:        string
  usuario:      UsuarioMe
  login_em:     string   // ISO string
}

// ── Sync ─────────────────────────────────────────────────────
export interface SyncStatus {
  sap_snapshot_atualizado_em: string | null
  kpi_calculado_em:           string | null
  ultima_execucao_status:     string | null
  ultima_execucao_em:         string | null
  ultima_execucao_origem:     string | null
  ultima_execucao_mensagem:   string | null
}

// ── KPI ──────────────────────────────────────────────────────
export interface KpiProjeto {
  projeto_id:        number
  nome:              string
  progresso:         number | null
  pontos_total:      number
  pontos_concluidos: number
}

export interface KpiProjetosResponse {
  sap_snapshot_atualizado_em: string | null
  kpi_calculado_em:           string | null
  projetos:                   KpiProjeto[]
}

export interface Inconsistencia {
  ut_id:         number
  ocorrencia:    string
  ciclo_modelo:  string
  projeto_nome:  string | null
  subfase_nome:  string | null
  nome_executor: string | null
}

export interface InconsistenciasResponse {
  total:                      number
  sap_snapshot_atualizado_em: string | null
  itens:                      Inconsistencia[]
}

// ── Alertas (inbox) ─────────────────────────────────────────
export type AlertaSeveridade = 'info' | 'warn' | 'error'

export interface Alerta {
  id:         string
  severidade: AlertaSeveridade
  titulo:     string
  mensagem:   string
  criado_em:  string   // ISO string
  lido:       boolean
}

// ── Log de acesso ─────────────────────────────────────────── 
export interface LogAcesso {
  login_em:      string
  ip?:           string
  user_agent?:   string
}


export interface KpiDashboardResponse {
  sap_snapshot_atualizado_em: string | null
  kpi_calculado_em: string | null
  projetos_ativos: number
  blocos_sap_cadastrados: number
  progresso_geral: number | null
  pontos_totais: number
  pontos_realizados: number
  horas_previstas_producao_min: number
  horas_lancadas_producao_min: number
  hierarquia: Array<unknown>
  top_executor: unknown | null
  top_revisor: unknown | null
  top_executores_subfase: Array<Record<string, unknown>>
  top_revisores_subfase: Array<Record<string, unknown>>
}

// ── Dashboard do operador ─────────────────────────────────────

export interface PontosSubfaseResposta {
  subfase_id: number
  subfase_nome: string
  pontos: number
}

export interface BlocoDetalheUsuario {
  bloco_id: number
  bloco_nome: string
  projeto_nome: string
  pontos_total_bloco: number
  pontos_usuario_bloco: number
  como_executor: PontosSubfaseResposta[]
  como_revisor: PontosSubfaseResposta[]
  como_corretor: PontosSubfaseResposta[]
}

export interface DiaHorasResposta {
  data: string
  minutos_previstos: number
  minutos_lancados: number
}

export interface MeuDashboardResponse {
  sap_snapshot_atualizado_em: string | null
  kpi_calculado_em: string | null
  blocos: BlocoDetalheUsuario[]
  pontos_total_geral: number
  pontos_usuario_geral: number
  horas_previstas_producao_min: number
  horas_lancadas_producao_min: number
  horas_lancadas_externas_min: number
  timeline: DiaHorasResposta[]
}
