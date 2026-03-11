// ============================================================
// Tipos da Agenda — espelha schemas do backend
// ============================================================

// ── Enums ────────────────────────────────────────────────────

export type FaixaMinuto = 'NORMAL' | 'EXTRA'

export type GrupoAtividade = 'PRODUCAO' | 'INDISPONIBILIDADE' | 'AJUSTE'

export type CodigoAtividade = 
  | 'BLOCO' 
  | 'EXTERNA' 
  | 'AJUSTE' 
  | 'FERIAS' 
  | 'LICENCA' 
  | 'CURSO' 
  | 'AFASTAMENTO'

export type StatusDia = 'ABERTO' | 'CONSOLIDADO'

export type TipoIndisponibilidade = 'FERIAS' | 'LICENCA' | 'CURSO' | 'AFASTAMENTO'

export type TipoPendencia = 
  | 'SEM_LANCAMENTO' 
  | 'LANCAMENTO_INCOMPLETO' 
  | 'INDISPONIBILIDADE_NAO_TRATADA'
  | 'INCONSISTENCIA_CALENDARIO'

// ── Tipo de Atividade ────────────────────────────────────────

export interface TipoAtividade {
  id: number
  codigo: CodigoAtividade
  nome: string
  grupo: GrupoAtividade
  origem?: 'TIPO_ATIVIDADE' | 'BLOCO'
  bloco_id?: number | null
}

// ── Parâmetros de Capacidade ─────────────────────────────────

export interface ConfigTeto {
  teto_normal_min: number
  teto_extra_min: number
  vigencia_inicio: string
  vigencia_fim: string | null
  configurado_em: string | null
  configurado_por: number | null
}

export interface ConfigTetoInput {
  teto_normal_min: number
  teto_extra_min: number
}

// ── Planejamento ─────────────────────────────────────────────

export interface Planejamento {
  id: number
  usuario_id: number
  data: string
  bloco_id: number | null
  minutos_planejados_normais: number
  minutos_planejados_extras: number
  descricao: string | null
  criado_por: number
  criado_em: string
  atualizado_em: string
}

export interface PlanejamentoInput {
  usuario_id: number
  data: string
  bloco_id: number | null
  minutos_planejados_normais: number
  minutos_planejados_extras?: number
  descricao?: string | null
}

export interface PlanejamentoUpdateInput {
  minutos_planejados_normais?: number
  minutos_planejados_extras?: number
  descricao?: string | null
}

export interface PlanejamentoLoteInput {
  usuario_ids: number[]
  datas: string[]
  bloco_id: number | null
  minutos_planejados_normais: number
  minutos_planejados_extras?: number
  descricao?: string | null
}

export interface PlanejamentoRemocaoLoteInput {
  usuario_ids: number[]
  datas: string[]
}

// ── Lançamento ───────────────────────────────────────────────

export interface Lancamento {
  id: number
  usuario_id: number
  data_lancamento: string
  bloco_id: number | null
  tipo_atividade_id: number
  tipo_atividade_codigo: CodigoAtividade
  tipo_atividade_nome: string
  faixa_minuto: FaixaMinuto
  minutos: number
  descricao: string | null
  criado_por: number
  atualizado_por: number | null
  criado_em: string
  atualizado_em: string
  alertas?: string[]
}

export interface LancamentoInput {
  data: string
  bloco_id: number | null
  tipo_atividade: CodigoAtividade
  faixa: FaixaMinuto
  minutos: number
  descricao?: string | null
}

export interface LancamentoAdminInput extends LancamentoInput {
  usuario_id: number
}

export interface LancamentoUpdateInput {
  minutos?: number
  descricao?: string | null
}

// ── Apontamento (resumo para visualização) ───────────────────

export interface ApontamentoResumo {
  id: number
  data: string
  bloco_id: number | null
  bloco_nome?: string | null
  tipo_atividade: CodigoAtividade
  minutos: number
  faixa: FaixaMinuto
}

// ── Dia da Agenda ────────────────────────────────────────────

export interface DiaDaAgenda {
  data: string
  status: StatusDia
  eh_dia_util: boolean
  eh_feriado: boolean
  eh_indisponivel: boolean
  tipo_indisponibilidade: TipoIndisponibilidade | null
  teto_normal_min: number
  teto_extra_min: number
  apontado_normal_min: number
  apontado_extra_min: number
  minutos_ociosos: number
  planejamento: Planejamento[]
  lancamentos: ApontamentoResumo[]
}

export interface AgendaCompleta {
  usuario_id: number
  data_inicio: string
  data_fim: string
  dias: DiaDaAgenda[]
}

// ── Resumo de Capacidade ─────────────────────────────────────

export interface ResumoCapacidade {
  usuario_id: number
  data_inicio: string
  data_fim: string
  bloco_id: number | null
  minutos_previstos_normais: number
  minutos_realizados_bloco_normais: number
  minutos_perdidos_externas_normais: number
  minutos_nao_alocados: number
  minutos_ociosos: number
  minutos_extras_bloco: number
  minutos_extras_externas: number
  minutos_extras_totais: number
}

export interface CapacidadePeriodo {
  resumo: ResumoCapacidade
  detalhes_por_dia: DiaDaAgenda[]
}

// ── Feriados ─────────────────────────────────────────────────

export interface Feriado {
  id: number
  data: string
  descricao: string
  criado_por: number
  criado_em: string
}

export interface FeriadoInput {
  data: string
  descricao: string
}

// ── Indisponibilidades ───────────────────────────────────────

export interface Indisponibilidade {
  id: number
  usuario_id: number
  tipo_atividade_id: number
  tipo: TipoIndisponibilidade
  data_inicio: string
  data_fim: string
  descricao: string | null
  criado_por: number
  criado_em: string
}

export interface IndisponibilidadeInput {
  usuario_id: number
  tipo: TipoIndisponibilidade
  data_inicio: string
  data_fim: string
  descricao?: string | null
}

// ── Consolidação ─────────────────────────────────────────────

export interface Pendencia {
  usuario_id: number
  usuario_nome?: string | null
  data: string
  tipo: TipoPendencia
  motivo: string
}

export interface ConsolidacaoInput {
  data_inicio: string
  data_fim: string
  usuarios_ids?: number[]
  ignorar_pendencias?: boolean
}

export interface ConsolidacaoResult {
  consolidado: boolean
  pendencias: Pendencia[]
  mensagem: string
}

// ── Respostas genéricas ──────────────────────────────────────

export interface RemovidoResponse {
  removido: boolean
  mensagem?: string
}

// ── Bloco (para seleção) ─────────────────────────────────────

export interface Bloco {
  id: number
  nome: string
  projeto_id: number
  projeto_nome?: string
}

// ── Usuário resumido (para admin) ────────────────────────────

export interface UsuarioResumo {
  id: number
  nome: string
  nome_guerra: string | null
}

// ── View helpers ─────────────────────────────────────────────

export type CalendarView = 'day' | 'week' | 'month' | 'year'

export interface DateRange {
  start: Date
  end: Date
}

export interface CalendarDay {
  date: Date
  isCurrentMonth: boolean
  isToday: boolean
  isWeekend: boolean
  agenda?: DiaDaAgenda
}
