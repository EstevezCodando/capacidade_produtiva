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


// ── Dashboard Admin — novos tipos de controle gerencial ──────

export interface ContribuidorBloco {
  usuario_id: number
  nome_guerra: string
  pontos: number
  percentual: number  // % dos pontos do bloco
}

export interface BlocoDestaque {
  bloco_id: number
  bloco_nome: string
  projeto_nome: string
  lote_nome: string
  uts_total: number
  uts_concluidas: number
  uts_em_andamento: number
  uts_sem_inicio: number
  pontos_total: number
  pontos_realizados: number
  progresso: number | null
  top_executores: ContribuidorBloco[]
  top_revisores: ContribuidorBloco[]
}

export interface AlertaNotaAusente {
  ut_id: number
  bloco_nome: string
  lote_nome: string
  subfase_nome: string
  executor_id: number | null
  nome_executor: string | null
  revisor_id: number | null
  nome_revisor: string | null
  cor_atividade_id: number | null  // ID da atividade de correção
  ocorrencia: string               // NOTA_AUSENTE | NOTA_INVALIDA
}

export interface RankingOperador {
  posicao: number
  usuario_id: number
  nome_guerra: string
  pontos_executor: number
  pontos_revisor: number
  pontos_corretor: number
  pontos_total: number
  uts_executadas: number
  uts_revisadas: number
}

export interface SemanaVelocidade {
  semana_label: string   // "DD/MM"
  semana_inicio: string  // "YYYY-MM-DD"
  uts_concluidas: number
  pontos_realizados: number
}

export interface DistribuicaoCiclo {
  ciclo: string
  quantidade: number
  percentual: number
}

export interface SubfaseDisponivel {
  subfase_id: number
  subfase_nome: string
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
  timeline_mensal: MesTrilha[]
  blocos_destaque: BlocoDestaque[]
  alertas_nota: AlertaNotaAusente[]
  ranking_operadores: RankingOperador[]
  velocidade_semanal: SemanaVelocidade[]
  distribuicao_ciclos: DistribuicaoCiclo[]
  bloco_filtro_id?: number | null
  bloco_filtro_nome?: string | null
  subfase_filtro_id?: number | null
  subfase_filtro_nome?: string | null
  subfases_disponiveis?: SubfaseDisponivel[]
}

// ── Dashboard do operador ─────────────────────────────────────

export interface PontosSubfaseResposta {
  subfase_id: number
  subfase_nome: string
  pontos: number                   // pontos do usuário nesta subfase/papel
  pontos_total_subfase: number     // total alocado na subfase/bloco (fluxo_ut)
}

export interface BlocoDetalheUsuario {
  bloco_id: number
  bloco_nome: string
  projeto_nome: string
  pontos_total_bloco: number       // total distribuído a todos os usuários
  pontos_usuario_bloco: number     // contribuição do usuário
  pontos_alocados_bloco: number    // total alocado no bloco (fluxo_ut) — base 100%
  como_executor: PontosSubfaseResposta[]
  como_revisor: PontosSubfaseResposta[]
  como_corretor: PontosSubfaseResposta[]
}

export interface DiaHorasResposta {
  data: string
  minutos_previstos: number
  minutos_lancados: number
  minutos_lancados_normal: number
}

export interface PizzaFatia {
  nome: string
  cor: string
  minutos: number
  percentual: number
}

export interface PizzaDistribuicaoResponse {
  mes: string
  total_capacidade_min: number
  nao_alocado_min: number
  fatias: PizzaFatia[]
}

export interface UsuarioResumo {
  id: number
  nome: string
  nome_guerra: string | null
}

export interface MesTrilha {
  mes: string                        // "YYYY-MM-DD" 1º do mês
  minutos_previstos_acum: number     // J: previsto acumulado
  minutos_lancados_normal_acum: number  // K: normal acumulado
  minutos_lancados_total_acum: number   // P: normal+extra acumulado
  minutos_divergente_acum?: number   // D: horas fora do bloco planejado (só com filtro ativo)
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
  timeline_mensal: MesTrilha[]
}
