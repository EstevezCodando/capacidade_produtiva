import { apiClient } from './client'
import type {
  AgendaCompleta,
  Bloco,
  CapacidadePeriodo,
  ConfigTeto,
  ConfigTetoInput,
  ConsolidacaoInput,
  ConsolidacaoResult,
  DesconsolidacaoInput,
  DesconsolidacaoResult,
  Feriado,
  FeriadoInput,
  Indisponibilidade,
  IndisponibilidadeInput,
  Lancamento,
  LancamentoAdminInput,
  LancamentoAdminLoteInput,
  LancamentoInput,
  LancamentoLoteInput,
  LancamentoLoteResult,
  LancamentoUpdateInput,
  Planejamento,
  PlanejamentoInput,
  PlanejamentoLoteInput,
  PlanejamentoRemocaoLoteInput,
  PlanejamentoUpdateInput,
  RemovidoResponse,
  TipoAtividade,
  UsuarioResumo,
} from '@/types/agenda'

export async function getMeuPlanejamento(dataInicio: string, dataFim: string): Promise<AgendaCompleta> {
  const res = await apiClient.get<AgendaCompleta>('/agenda/meu-planejamento', {
    params: { data_inicio: dataInicio, data_fim: dataFim },
  })
  return res.data
}

export async function getMeusLancamentos(dataInicio: string, dataFim: string): Promise<Lancamento[]> {
  const res = await apiClient.get<Lancamento[]>('/agenda/meus-lancamentos', {
    params: { data_inicio: dataInicio, data_fim: dataFim },
  })
  return res.data
}

export async function criarLancamento(input: LancamentoInput): Promise<Lancamento> {
  const res = await apiClient.post<Lancamento>('/agenda/lancamento', input)
  return res.data
}

export async function editarLancamento(id: number, input: LancamentoUpdateInput): Promise<Lancamento> {
  const res = await apiClient.put<Lancamento>(`/agenda/lancamento/${id}`, input)
  return res.data
}

export async function removerLancamento(id: number): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/lancamento/${id}`)
  return res.data
}

export async function getAgendaUsuario(usuarioId: number, dataInicio: string, dataFim: string): Promise<AgendaCompleta> {
  const res = await apiClient.get<AgendaCompleta>(`/agenda/usuario/${usuarioId}`, {
    params: { data_inicio: dataInicio, data_fim: dataFim },
  })
  return res.data
}

export async function criarPlanejamento(input: PlanejamentoInput): Promise<Planejamento> {
  const res = await apiClient.post<Planejamento>('/agenda/planejamento', input)
  return res.data
}

export async function editarPlanejamento(id: number, input: PlanejamentoUpdateInput): Promise<Planejamento> {
  const res = await apiClient.put<Planejamento>(`/agenda/planejamento/${id}`, input)
  return res.data
}

export async function criarPlanejamentoLote(input: PlanejamentoLoteInput): Promise<Planejamento[]> {
  const res = await apiClient.post<Planejamento[]>('/agenda/planejamento/lote', input)
  return res.data
}

export async function removerPlanejamentoLote(input: PlanejamentoRemocaoLoteInput): Promise<RemovidoResponse> {
  const res = await apiClient.post<RemovidoResponse>('/agenda/planejamento/remover-lote', input)
  return res.data
}

export async function removerPlanejamento(id: number): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/planejamento/${id}`)
  return res.data
}

export async function criarLancamentoAdmin(input: LancamentoAdminInput): Promise<Lancamento> {
  const res = await apiClient.post<Lancamento>('/agenda/lancamento-admin', input)
  return res.data
}

export async function editarLancamentoAdmin(id: number, input: LancamentoUpdateInput): Promise<Lancamento> {
  const res = await apiClient.put<Lancamento>(`/agenda/lancamento-admin/${id}`, input)
  return res.data
}

export async function removerLancamentoAdmin(id: number): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/lancamento-admin/${id}`)
  return res.data
}

export async function criarLancamentoLote(input: LancamentoLoteInput): Promise<LancamentoLoteResult> {
  const res = await apiClient.post<LancamentoLoteResult>('/agenda/lancamento/lote', input)
  return res.data
}

export async function criarLancamentoAdminLote(input: LancamentoAdminLoteInput): Promise<LancamentoLoteResult> {
  const res = await apiClient.post<LancamentoLoteResult>('/agenda/lancamento-admin/lote', input)
  return res.data
}

export async function getFeriados(): Promise<{ feriados: Feriado[] }> {
  try {
    const res = await apiClient.get<{ feriados: Feriado[] }>('/capacidade/feriados')
    return res.data
  } catch {
    return { feriados: [] }
  }
}

export async function criarFeriado(input: FeriadoInput): Promise<Feriado> {
  const res = await apiClient.post<Feriado>('/agenda/feriado', input)
  return res.data
}

export async function removerFeriado(id: number): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/feriado/${id}`)
  return res.data
}

export async function criarIndisponibilidade(input: IndisponibilidadeInput): Promise<Indisponibilidade> {
  const res = await apiClient.post<Indisponibilidade>('/agenda/indisponibilidade', input)
  return res.data
}

export async function removerIndisponibilidade(id: number): Promise<RemovidoResponse> {
  const res = await apiClient.delete<RemovidoResponse>(`/agenda/indisponibilidade/${id}`)
  return res.data
}

export async function getConfigTeto(): Promise<ConfigTeto> {
  try {
    const res = await apiClient.get<ConfigTeto>('/capacidade/config')
    return res.data
  } catch {
    return {
      teto_normal_min: 360,
      teto_extra_min: 240,
      vigencia_inicio: '',
      vigencia_fim: null,
      configurado_em: null,
      configurado_por: null,
    }
  }
}

export async function atualizarConfigTeto(input: ConfigTetoInput): Promise<ConfigTeto> {
  const res = await apiClient.put<ConfigTeto>('/capacidade/config', input)
  return res.data
}

export async function getMeuPeriodo(dataInicio: string, dataFim: string, blocoId?: number): Promise<CapacidadePeriodo> {
  const res = await apiClient.get<CapacidadePeriodo>('/capacidade/meu-periodo', {
    params: {
      data_inicio: dataInicio,
      data_fim: dataFim,
      ...(blocoId ? { bloco_id: blocoId } : {}),
    },
  })
  return res.data
}

export async function getCapacidadeUsuario(usuarioId: number, dataInicio: string, dataFim: string, blocoId?: number): Promise<CapacidadePeriodo> {
  const res = await apiClient.get<CapacidadePeriodo>(`/capacidade/usuario/${usuarioId}`, {
    params: {
      data_inicio: dataInicio,
      data_fim: dataFim,
      ...(blocoId ? { bloco_id: blocoId } : {}),
    },
  })
  return res.data
}

export async function getStatusDias(dataInicio: string, dataFim: string): Promise<{ dias: Array<{ data: string; status: string }> }> {
  const res = await apiClient.get<{ dias: Array<{ data: string; status: string }> }>('/capacidade/status', {
    params: { data_inicio: dataInicio, data_fim: dataFim },
  })
  return res.data
}

export async function consolidarPeriodo(input: ConsolidacaoInput): Promise<ConsolidacaoResult> {
  const res = await apiClient.post<ConsolidacaoResult>('/capacidade/consolidar-periodo', input)
  return res.data
}

export async function desconsolidarPeriodo(input: DesconsolidacaoInput): Promise<DesconsolidacaoResult> {
  const res = await apiClient.post<DesconsolidacaoResult>('/capacidade/desconsolidar-periodo', input)
  return res.data
}

/**
 * Baixa o CSV de inconsistências diretamente no navegador.
 * Retorna o conteúdo CSV como string para que o chamador possa decidir
 * se quer disparar o download ou apenas apresentar os dados.
 */
export async function exportarInconsistenciasCSV(
  dataInicio: string,
  dataFim: string,
  usuariosIds: number[],
): Promise<void> {
  const params = new URLSearchParams({
    data_inicio: dataInicio,
    data_fim: dataFim,
    usuarios_ids: usuariosIds.join(','),
  })
  // Usamos fetch direto para obter o blob do CSV
  const token = localStorage.getItem('token') ?? sessionStorage.getItem('token') ?? ''
  const resp = await fetch(
    `${apiClient.defaults.baseURL}/capacidade/exportar-sem-lancamento?${params.toString()}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  if (!resp.ok) throw new Error('Falha ao exportar CSV')
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `inconsistencias_${dataInicio}_${dataFim}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function getBlocos(): Promise<Bloco[]> {
  const res = await apiClient.get<Bloco[]>('/blocos')
  return res.data
}

export async function getUsuarios(): Promise<UsuarioResumo[]> {
  try {
    const res = await apiClient.get<UsuarioResumo[] | { itens?: UsuarioResumo[] }>('/usuarios')
    return Array.isArray(res.data) ? res.data : (res.data.itens ?? [])
  } catch {
    return []
  }
}

export async function getTiposAtividade(): Promise<TipoAtividade[]> {
  try {
    const res = await apiClient.get<TipoAtividade[] | { itens?: TipoAtividade[] }>('/atividades/tipos')
    return Array.isArray(res.data) ? res.data : (res.data.itens ?? [])
  } catch {
    return []
  }
}


export async function getTiposAtividadeConfiguracao(): Promise<TipoAtividade[]> {
  const res = await apiClient.get<TipoAtividade[]>('/capacidade/tipos-atividade')
  return res.data
}

export async function atualizarCorTipoAtividade(tipoAtividadeId: number, cor: string): Promise<TipoAtividade> {
  const res = await apiClient.put<TipoAtividade>(`/capacidade/tipos-atividade/${tipoAtividadeId}/cor`, { cor })
  return res.data
}
