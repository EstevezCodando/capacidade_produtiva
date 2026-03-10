// ============================================================
// API — Endpoints de Agenda e Capacidade
// ============================================================
import { apiClient } from './client'
import type {
  AgendaCompleta,
  Lancamento,
  LancamentoInput,
  LancamentoAdminInput,
  LancamentoUpdateInput,
  Planejamento,
  PlanejamentoInput,
  PlanejamentoUpdateInput,
  Feriado,
  FeriadoInput,
  Indisponibilidade,
  IndisponibilidadeInput,
  ConfigTeto,
  ConfigTetoInput,
  ConsolidacaoInput,
  ConsolidacaoResult,
  CapacidadePeriodo,
  RemovidoResponse,
  Bloco,
  UsuarioResumo,
} from '@/types/agenda'

// ══════════════════════════════════════════════════════════════
// Agenda - Operador
// ══════════════════════════════════════════════════════════════

export async function getMeuPlanejamento(
  dataInicio: string,
  dataFim: string
): Promise<AgendaCompleta> {
  const res = await apiClient.get<AgendaCompleta>('/agenda/meu-planejamento', {
    params: { data_inicio: dataInicio, data_fim: dataFim }
  })
  return res.data
}

export async function getMeusLancamentos(
  dataInicio: string,
  dataFim: string
): Promise<Lancamento[]> {
  const res = await apiClient.get<Lancamento[]>('/agenda/meus-lancamentos', {
    params: { data_inicio: dataInicio, data_fim: dataFim }
  })
  return res.data
}

export async function criarLancamento(
  input: LancamentoInput
): Promise<Lancamento> {
  const res = await apiClient.post<Lancamento>('/agenda/lancamento', input)
  return res.data
}

export async function editarLancamento(
  id: number,
  input: LancamentoUpdateInput
): Promise<Lancamento> {
  const res = await apiClient.put<Lancamento>(`/agenda/lancamento/${id}`, input)
  return res.data
}

export async function removerLancamento(
  id: number
): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/lancamento/${id}`)
  return res.data
}

// ══════════════════════════════════════════════════════════════
// Agenda - Admin
// ══════════════════════════════════════════════════════════════

export async function getAgendaUsuario(
  usuarioId: number,
  dataInicio: string,
  dataFim: string
): Promise<AgendaCompleta> {
  const res = await apiClient.get<AgendaCompleta>(`/agenda/usuario/${usuarioId}`, {
    params: { data_inicio: dataInicio, data_fim: dataFim }
  })
  return res.data
}

export async function criarPlanejamento(
  input: PlanejamentoInput
): Promise<Planejamento> {
  const res = await apiClient.post<Planejamento>('/agenda/planejamento', input)
  return res.data
}

export async function editarPlanejamento(
  id: number,
  input: PlanejamentoUpdateInput
): Promise<Planejamento> {
  const res = await apiClient.put<Planejamento>(`/agenda/planejamento/${id}`, input)
  return res.data
}

export async function removerPlanejamento(
  id: number
): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/planejamento/${id}`)
  return res.data
}

export async function criarLancamentoAdmin(
  input: LancamentoAdminInput
): Promise<Lancamento> {
  const res = await apiClient.post<Lancamento>('/agenda/lancamento-admin', input)
  return res.data
}

export async function editarLancamentoAdmin(
  id: number,
  input: LancamentoUpdateInput
): Promise<Lancamento> {
  const res = await apiClient.put<Lancamento>(`/agenda/lancamento-admin/${id}`, input)
  return res.data
}

export async function removerLancamentoAdmin(
  id: number
): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/lancamento-admin/${id}`)
  return res.data
}

// ══════════════════════════════════════════════════════════════
// Feriados
// ══════════════════════════════════════════════════════════════

export async function getFeriados(): Promise<{ feriados: Feriado[] }> {
  const res = await apiClient.get<{ feriados: Feriado[] }>('/capacidade/feriados')
  return res.data
}

export async function criarFeriado(input: FeriadoInput): Promise<Feriado> {
  const res = await apiClient.post<Feriado>('/agenda/feriado', input)
  return res.data
}

export async function removerFeriado(id: number): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/feriado/${id}`)
  return res.data
}

// ══════════════════════════════════════════════════════════════
// Indisponibilidades
// ══════════════════════════════════════════════════════════════

export async function criarIndisponibilidade(
  input: IndisponibilidadeInput
): Promise<Indisponibilidade> {
  const res = await apiClient.post<Indisponibilidade>('/agenda/indisponibilidade', input)
  return res.data
}

export async function removerIndisponibilidade(
  id: number
): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/indisponibilidade/${id}`)
  return res.data
}

// ══════════════════════════════════════════════════════════════
// Capacidade e Configuração
// ══════════════════════════════════════════════════════════════

export async function getConfigTeto(): Promise<ConfigTeto> {
  const res = await apiClient.get<ConfigTeto>('/capacidade/config')
  return res.data
}

export async function atualizarConfigTeto(
  input: ConfigTetoInput
): Promise<ConfigTeto> {
  const res = await apiClient.put<ConfigTeto>('/capacidade/config', input)
  return res.data
}

export async function getMeuPeriodo(
  dataInicio: string,
  dataFim: string,
  blocoId?: number
): Promise<CapacidadePeriodo> {
  const res = await apiClient.get<CapacidadePeriodo>('/capacidade/meu-periodo', {
    params: { 
      data_inicio: dataInicio, 
      data_fim: dataFim,
      ...(blocoId && { bloco_id: blocoId })
    }
  })
  return res.data
}

export async function getCapacidadeUsuario(
  usuarioId: number,
  dataInicio: string,
  dataFim: string,
  blocoId?: number
): Promise<CapacidadePeriodo> {
  const res = await apiClient.get<CapacidadePeriodo>(`/capacidade/usuario/${usuarioId}`, {
    params: { 
      data_inicio: dataInicio, 
      data_fim: dataFim,
      ...(blocoId && { bloco_id: blocoId })
    }
  })
  return res.data
}

// ══════════════════════════════════════════════════════════════
// Consolidação
// ══════════════════════════════════════════════════════════════

export async function getStatusDias(
  dataInicio: string,
  dataFim: string
): Promise<{ dias: Array<{ data: string; status: string }> }> {
  const res = await apiClient.get('/capacidade/status', {
    params: { data_inicio: dataInicio, data_fim: dataFim }
  })
  return res.data
}

export async function consolidarPeriodo(
  input: ConsolidacaoInput
): Promise<ConsolidacaoResult> {
  const res = await apiClient.post<ConsolidacaoResult>('/capacidade/consolidar-periodo', input)
  return res.data
}

// ══════════════════════════════════════════════════════════════
// Dados auxiliares
// ══════════════════════════════════════════════════════════════

export async function getBlocos(): Promise<Bloco[]> {
  // Endpoint pode variar - ajustar conforme backend
  const res = await apiClient.get<Bloco[]>('/blocos')
  return res.data
}

export async function getUsuarios(): Promise<UsuarioResumo[]> {
  // Endpoint pode variar - ajustar conforme backend
  const res = await apiClient.get<UsuarioResumo[]>('/usuarios')
  return res.data
}

export async function getTiposAtividade() {
  const res = await apiClient.get('/atividades/tipos')
  return res.data
}
