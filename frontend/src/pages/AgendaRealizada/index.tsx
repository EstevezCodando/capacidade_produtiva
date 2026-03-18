import {
  getAgendaUsuario,
  getBlocos,
  getConfigTeto,
  getTiposAtividade,
  getUsuarios,
} from '@/api/agenda'
import ConsolidacaoModal from '@/components/agenda/ConsolidacaoModal'
import DayDetailPanel from '@/components/agenda/DayDetailPanel'
import LancamentoForm from '@/components/agenda/LancamentoForm'
import CalendarGrid from '@/components/calendar/CalendarGrid'
import CalendarHeader from '@/components/calendar/CalendarHeader'
import { Card, Input, Skeleton, StatCard } from '@/components/ui/Common'
import { useAuth } from '@/context/AuthContext'
import { useAgendaData, useCalendarNavigation } from '@/hooks/useCalendar'
import type { AgendaCompleta, ApontamentoResumo, DiaDaAgenda, Lancamento, TipoAtividade, UsuarioResumo } from '@/types/agenda'
import { useQuery } from '@tanstack/react-query'
import { format, isAfter, startOfDay } from 'date-fns'
import { useEffect, useMemo, useRef, useState } from 'react'
import styles from './AgendaPage.module.css'

interface SegmentoBarraDia {
  cor: string
  minutos: number
  percentual?: number
}

interface UsuarioResumoDia {
  usuarioId: number
  nome: string
  minutosLancados: number
  minutosNormais: number
  minutosExtras: number
  capacidadeMaxima: number
  segmentos: SegmentoBarraDia[]
}

function obterNomeUsuario(usuario: UsuarioResumo): string {
  return usuario.nome_guerra?.trim() || usuario.nome
}


function normalizarCorHex(cor?: string | null): string {
  const valor = (cor ?? '').trim().toUpperCase()
  if (/^#[0-9A-F]{6}$/.test(valor)) return valor
  return 'var(--accent)'
}

function criarResumoUsuarioDia(usuarioId: number, nome: string, capacidadeMaxima: number): UsuarioResumoDia {
  return {
    usuarioId,
    nome,
    minutosLancados: 0,
    minutosNormais: 0,
    minutosExtras: 0,
    capacidadeMaxima,
    segmentos: [],
  }
}

function acumularSegmento(segmentos: SegmentoBarraDia[], cor: string, minutos: number) {
  if (minutos <= 0) return
  const corNormalizada = normalizarCorHex(cor)
  const existente = segmentos.find((item) => item.cor === corNormalizada)
  if (existente) {
    existente.minutos += minutos
    return
  }
  segmentos.push({ cor: corNormalizada, minutos })
}

function calcularSegmentosPercentuais(segmentos: SegmentoBarraDia[], capacidadeTotal: number): SegmentoBarraDia[] {
  if (capacidadeTotal <= 0 || segmentos.length === 0) return []
  return segmentos
    .filter((segmento) => segmento.minutos > 0)
    .map((segmento) => ({
      ...segmento,
      percentual: Math.min(100, (segmento.minutos / capacidadeTotal) * 100),
    }))
}

function podeLancarNoDia(data: Date, dia?: DiaDaAgenda) {
  if (!dia) return false
  if (dia.status === 'CONSOLIDADO') return false
  return !isAfter(startOfDay(data), startOfDay(new Date()))
}

function enriquecerLancamentoResumo(
  lancamento: ApontamentoResumo,
  tiposAtividade: TipoAtividade[],
  nomeUsuario?: string,
): ApontamentoResumo {
  const tipo = tiposAtividade.find((item) => item.codigo === lancamento.tipo_atividade)
  return {
    ...lancamento,
    usuario_nome: nomeUsuario ?? lancamento.usuario_nome ?? null,
    tipo_atividade_nome: lancamento.tipo_atividade_nome ?? tipo?.nome ?? lancamento.tipo_atividade,
    tipo_atividade_cor: lancamento.tipo_atividade_cor ?? tipo?.cor ?? 'var(--accent)',
  }
}

function consolidarDia(data: string, dias: DiaDaAgenda[], tiposAtividade: TipoAtividade[], nomesUsuarios: Map<number, string>): DiaDaAgenda {
  const base = dias[0]
  const lancamentos = dias.flatMap((dia) =>
    dia.lancamentos.map((lancamento) => enriquecerLancamentoResumo(
      {
        ...lancamento,
        usuario_id: lancamento.usuario_id ?? undefined,
      },
      tiposAtividade,
      lancamento.usuario_id ? nomesUsuarios.get(lancamento.usuario_id) : undefined,
    )),
  )

  return {
    ...base,
    data,
    status: dias.every((dia) => dia.status === 'CONSOLIDADO') ? 'CONSOLIDADO' : 'ABERTO',
    teto_normal_min: dias.reduce((acc, dia) => acc + dia.teto_normal_min, 0),
    teto_extra_min: dias.reduce((acc, dia) => acc + dia.teto_extra_min, 0),
    apontado_normal_min: dias.reduce((acc, dia) => acc + dia.apontado_normal_min, 0),
    apontado_extra_min: dias.reduce((acc, dia) => acc + dia.apontado_extra_min, 0),
    minutos_ociosos: dias.reduce((acc, dia) => acc + dia.minutos_ociosos, 0),
    eh_feriado: dias.some((dia) => dia.eh_feriado),
    eh_indisponivel: dias.some((dia) => dia.eh_indisponivel),
    planejamento: [],
    lancamentos,
  }
}

export default function AgendaRealizada() {
  const { ehAdmin, usuario } = useAuth()
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  const calendar = useCalendarNavigation({ initialView: 'month' })

  const [selectedUsuarioIds, setSelectedUsuarioIds] = useState<number[]>([])
  const [usuariosOpen, setUsuariosOpen] = useState(false)
  const [filtroUsuarios, setFiltroUsuarios] = useState('')
  const [lancamentoOpen, setLancamentoOpen] = useState(false)
  const [consolidacaoOpen, setConsolidacaoOpen] = useState(false)
  const [lancamentoDate, setLancamentoDate] = useState<Date | null>(null)
  const [lancamentoEdicao, setLancamentoEdicao] = useState<Lancamento | null>(null)
  const [detailPanelOpen, setDetailPanelOpen] = useState(false)

  const { data: usuarios = [], isLoading: loadingUsuarios } = useQuery({
    queryKey: ['usuarios'],
    queryFn: getUsuarios,
    enabled: ehAdmin,
    staleTime: 60_000,
  })

  const { data: blocos = [] } = useQuery({
    queryKey: ['blocos'],
    queryFn: getBlocos,
    staleTime: 60_000,
  })

  const { data: tiposAtividade = [] } = useQuery({
    queryKey: ['tipos-atividade'],
    queryFn: getTiposAtividade,
    staleTime: 60_000,
  })

  const { data: configTeto } = useQuery({
    queryKey: ['config-teto'],
    queryFn: getConfigTeto,
    staleTime: 60_000,
  })

  const usuarioIdPrincipal = useMemo(() => {
    if (!ehAdmin) return usuario?.usuario_id
    if (selectedUsuarioIds.length > 0) return selectedUsuarioIds[0]
    return usuario?.usuario_id
  }, [ehAdmin, selectedUsuarioIds, usuario?.usuario_id])

  const { agenda, isLoading, isError } = useAgendaData({
    usuarioId: usuarioIdPrincipal,
    isAdmin: ehAdmin,
    dataInicio: calendar.formatForApi(calendar.dateRange.start),
    dataFim: calendar.formatForApi(calendar.dateRange.end),
    enabled: !!usuarioIdPrincipal,
  })

  const idsUsuariosPainel = useMemo(() => {
    if (ehAdmin) {
      if (selectedUsuarioIds.length > 0) return selectedUsuarioIds
      return usuarioIdPrincipal ? [usuarioIdPrincipal] : []
    }
    return usuario?.usuario_id ? [usuario.usuario_id] : []
  }, [ehAdmin, selectedUsuarioIds, usuarioIdPrincipal, usuario?.usuario_id])

  const agendasMultiplosUsuariosQuery = useQuery({
    queryKey: [
      'agenda-realizada-multiusuario',
      idsUsuariosPainel,
      calendar.dateRange.start.toISOString(),
      calendar.dateRange.end.toISOString(),
      ehAdmin,
    ],
    queryFn: async (): Promise<AgendaCompleta[]> => {
      if (!idsUsuariosPainel.length) return []
      if (!ehAdmin) {
        if (!agenda) return []
        return [agenda]
      }
      const resultados = await Promise.allSettled(
        idsUsuariosPainel.map((usuarioId) =>
          getAgendaUsuario(
            usuarioId,
            calendar.formatForApi(calendar.dateRange.start),
            calendar.formatForApi(calendar.dateRange.end),
          ),
        ),
      )
      return resultados
        .filter((resultado): resultado is PromiseFulfilledResult<AgendaCompleta> => resultado.status === 'fulfilled')
        .map((resultado) => resultado.value)
    },
    enabled: idsUsuariosPainel.length > 0 && (!!agenda || ehAdmin),
    staleTime: 30_000,
  })

  const agendasFonte = useMemo(() => {
    if (ehAdmin) return agendasMultiplosUsuariosQuery.data ?? []
    return agenda ? [agenda] : []
  }, [agenda, agendasMultiplosUsuariosQuery.data, ehAdmin])

  const usuariosSelecionados = useMemo(
    () => usuarios.filter((item) => selectedUsuarioIds.includes(item.id)),
    [usuarios, selectedUsuarioIds],
  )

  const usuariosFiltrados = useMemo(() => {
    const termo = filtroUsuarios.trim().toLowerCase()
    if (!termo) return usuarios
    return usuarios.filter((item) => {
      const nomeCurto = obterNomeUsuario(item).toLowerCase()
      const nomeCompleto = item.nome.toLowerCase()
      return nomeCurto.includes(termo) || nomeCompleto.includes(termo)
    })
  }, [filtroUsuarios, usuarios])

  const mapaUsuariosPorId = useMemo(() => {
    const mapa = new Map<number, string>()
    for (const item of usuarios) {
      mapa.set(item.id, obterNomeUsuario(item))
    }
    if (usuario?.usuario_id) {
      mapa.set(usuario.usuario_id, usuario.nome_guerra || usuario.nome || 'Usuário atual')
    }
    return mapa
  }, [usuarios, usuario])

  const agendaSinteticaMap = useMemo(() => {
    const mapa = new Map<string, DiaDaAgenda>()
    const datasVisiveis = calendar.calendarDays.map((item) => format(item.date, 'yyyy-MM-dd'))

    for (const data of datasVisiveis) {
      const diasDoMesmoDia: DiaDaAgenda[] = []
      for (const agendaUsuario of agendasFonte) {
        const dia = agendaUsuario.dias.find((item) => item.data === data)
        if (!dia) continue
        diasDoMesmoDia.push({
          ...dia,
          planejamento: [],
          lancamentos: dia.lancamentos.map((lancamento) => enriquecerLancamentoResumo(
            {
              ...lancamento,
              usuario_id: agendaUsuario.usuario_id,
            },
            tiposAtividade,
            mapaUsuariosPorId.get(agendaUsuario.usuario_id),
          )),
        })
      }

      if (diasDoMesmoDia.length === 0) continue
      mapa.set(data, consolidarDia(data, diasDoMesmoDia, tiposAtividade, mapaUsuariosPorId))
    }

    return mapa
  }, [agendasFonte, calendar.calendarDays, mapaUsuariosPorId, tiposAtividade])

  const detalhesPorDia = useMemo(() => {
    const mapa = new Map<string, UsuarioResumoDia[]>()
    const capacidadePadraoMinutos = configTeto?.teto_normal_min ?? 360

    for (const agendaUsuario of agendasFonte) {
      const nomeUsuario = mapaUsuariosPorId.get(agendaUsuario.usuario_id) ?? `Usuário ${agendaUsuario.usuario_id}`
      for (const dia of agendaUsuario.dias) {
        const lista = mapa.get(dia.data) ?? []
        let resumo = lista.find((item) => item.usuarioId === agendaUsuario.usuario_id)
        if (!resumo) {
          resumo = criarResumoUsuarioDia(agendaUsuario.usuario_id, nomeUsuario, dia.teto_normal_min || capacidadePadraoMinutos)
          lista.push(resumo)
        }

        resumo.capacidadeMaxima = dia.teto_normal_min || capacidadePadraoMinutos
        resumo.minutosNormais = dia.apontado_normal_min
        resumo.minutosExtras = dia.apontado_extra_min
        resumo.minutosLancados = dia.apontado_normal_min + dia.apontado_extra_min

        for (const lancamento of dia.lancamentos) {
          const tipo = tiposAtividade.find((item) => item.codigo === lancamento.tipo_atividade)
          acumularSegmento(resumo.segmentos, tipo?.cor ?? 'var(--accent)', lancamento.minutos)
        }

        mapa.set(dia.data, [...lista].sort((a, b) => a.nome.localeCompare(b.nome)))
      }
    }

    return mapa
  }, [agendasFonte, configTeto?.teto_normal_min, mapaUsuariosPorId, tiposAtividade])

  const lancamentosPorId = useMemo(() => {
    const mapa = new Map<number, Lancamento>()
    for (const agendaDia of agendaSinteticaMap.values()) {
      for (const lancamento of agendaDia.lancamentos) {
        mapa.set(lancamento.id, {
          id: lancamento.id,
          usuario_id: lancamento.usuario_id ?? usuarioIdPrincipal ?? 0,
          data_lancamento: lancamento.data,
          bloco_id: lancamento.bloco_id,
          tipo_atividade_id: tiposAtividade.find((item) => item.codigo === lancamento.tipo_atividade)?.id ?? 0,
          tipo_atividade_codigo: lancamento.tipo_atividade,
          tipo_atividade_nome: lancamento.tipo_atividade_nome ?? String(lancamento.tipo_atividade),
          tipo_atividade_cor: lancamento.tipo_atividade_cor ?? 'var(--accent)',
          faixa_minuto: lancamento.faixa,
          minutos: lancamento.minutos,
          descricao: lancamento.descricao ?? null,
          criado_por: 0,
          atualizado_por: null,
          criado_em: '',
          atualizado_em: '',
        })
      }
    }
    return mapa
  }, [agendaSinteticaMap, tiposAtividade, usuarioIdPrincipal])

  const resumoPeriodo = useMemo(() => {
    let minutosNormais = 0
    let minutosExtras = 0
    let minutosCapacidade = 0
    let minutosOciosos = 0

    for (const dia of agendaSinteticaMap.values()) {
      minutosNormais += dia.apontado_normal_min
      minutosExtras += dia.apontado_extra_min
      minutosCapacidade += dia.teto_normal_min
      minutosOciosos += dia.minutos_ociosos
    }

    return {
      minutosNormais,
      minutosExtras,
      minutosCapacidade,
      minutosOciosos,
    }
  }, [agendaSinteticaMap])

  useEffect(() => {
    if (!ehAdmin) return
    function handleClickFora(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUsuariosOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickFora)
    return () => document.removeEventListener('mousedown', handleClickFora)
  }, [ehAdmin])

  function alternarUsuario(usuarioId: number) {
    setSelectedUsuarioIds((atual) => {
      if (atual.includes(usuarioId)) return atual.filter((id) => id !== usuarioId)
      return [...atual, usuarioId].sort((a, b) => a - b)
    })
  }

  function limparSelecaoUsuarios() {
    setSelectedUsuarioIds([])
  }

  function resumoUsuariosSelecionados() {
    if (!selectedUsuarioIds.length) return 'Selecione um ou mais usuários'
    if (usuariosSelecionados.length <= 2) return usuariosSelecionados.map(obterNomeUsuario).join(', ')
    return `${usuariosSelecionados.length} usuários selecionados`
  }

  function getDiaData(date: Date) {
    return agendaSinteticaMap.get(format(date, 'yyyy-MM-dd'))
  }

  function getHoverUsuarios(date: Date) {
    const lista = detalhesPorDia.get(format(date, 'yyyy-MM-dd')) ?? []
    return lista.map((item) => ({
      usuarioId: item.usuarioId,
      nome: item.nome,
      minutosPlanejados: item.minutosLancados,
      capacidadeMaxima: item.capacidadeMaxima,
      segmentos: calcularSegmentosPercentuais(item.segmentos, item.capacidadeMaxima),
    }))
  }

  function getCapacityDisplay(date: Date) {
    const lista = detalhesPorDia.get(format(date, 'yyyy-MM-dd')) ?? []
    if (lista.length === 0) return null
    const totalNormal = lista.reduce((acc, item) => acc + item.minutosNormais, 0)
    const totalExtra = lista.reduce((acc, item) => acc + item.minutosExtras, 0)
    const capacidadeTotal = Math.max(1, lista.reduce((acc, item) => acc + item.capacidadeMaxima, 0))
    const segmentosAgrupados: SegmentoBarraDia[] = []
    for (const item of lista) {
      for (const segmento of item.segmentos) {
        acumularSegmento(segmentosAgrupados, segmento.cor, segmento.minutos)
      }
    }

    return {
      totalMinutos: totalNormal,
      totalExtraMinutos: totalExtra,
      segmentos: calcularSegmentosPercentuais(segmentosAgrupados, capacidadeTotal),
    }
  }

  function handleDayClick(date: Date) {
    calendar.selectDate(date)
    setDetailPanelOpen(true)
  }

  function handleAddLancamento(date: Date) {
    setLancamentoDate(date)
    setLancamentoEdicao(null)
    setLancamentoOpen(true)
  }

  function handleEditLancamento(lancamentoId: number) {
    const lancamento = lancamentosPorId.get(lancamentoId)
    if (!lancamento) return
    setLancamentoDate(new Date(lancamento.data_lancamento))
    setLancamentoEdicao(lancamento)
    setLancamentoOpen(true)
  }

  const intervaloSelecionado = useMemo(() => {
    if (calendar.selectedRange) return calendar.selectedRange
    if (calendar.selectedDates.length === 1) {
      return { start: calendar.selectedDates[0], end: calendar.selectedDates[0] }
    }
    return null
  }, [calendar.selectedDates, calendar.selectedRange])

  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2 className={styles.sidebarTitle}>Agenda realizada</h2>
          <p className={styles.sidebarSubtitle}>
            Lançamentos reais da produção, com a mesma navegação e leitura visual da agenda prevista, mas sem misturar dados de planejamento.
          </p>
        </div>

        {ehAdmin ? (
          <div className={styles.userSelector} ref={dropdownRef}>
            <div className={styles.sectionHeaderCompact}>
              <span className={styles.selectorLabel}>Usuários</span>
              {selectedUsuarioIds.length > 0 && (
                <button type="button" className={styles.clearLink} onClick={limparSelecaoUsuarios}>
                  Limpar
                </button>
              )}
            </div>

            <button
              type="button"
              className={styles.userDropdownTrigger}
              onClick={() => setUsuariosOpen((atual) => !atual)}
              aria-expanded={usuariosOpen}
            >
              <div className={styles.userDropdownTriggerText}>
                <span className={styles.userDropdownTitle}>{resumoUsuariosSelecionados()}</span>
                <span className={styles.userDropdownHint}>Selecione um ou mais usuários para ver e lançar atividades</span>
              </div>
              <span className={styles.userDropdownMeta}>{selectedUsuarioIds.length}</span>
            </button>

            {usuariosOpen && (
              <div className={styles.userDropdownMenu}>
                <Input
                  className={styles.userSearchInput}
                  placeholder="Buscar usuário"
                  value={filtroUsuarios}
                  onChange={(evento) => setFiltroUsuarios(evento.target.value)}
                />
                <div className={styles.userDropdownList}>
                  {loadingUsuarios ? (
                    <div className={styles.userDropdownLoading}>Carregando usuários...</div>
                  ) : usuariosFiltrados.length === 0 ? (
                    <div className={styles.userDropdownLoading}>Nenhum usuário encontrado.</div>
                  ) : (
                    usuariosFiltrados.map((item) => {
                      const nomeCurto = obterNomeUsuario(item)
                      const nomeCompleto = item.nome.trim()
                      const selecionado = selectedUsuarioIds.includes(item.id)
                      return (
                        <label key={item.id} className={`${styles.userOption} ${selecionado ? styles.userOptionSelected : ''}`}>
                          <input type="checkbox" checked={selecionado} onChange={() => alternarUsuario(item.id)} />
                          <div className={styles.userOptionTextWrap}>
                            <span className={styles.userOptionText}>{nomeCurto}</span>
                            {nomeCompleto && nomeCompleto.toLowerCase() !== nomeCurto.toLowerCase() && (
                              <span className={styles.userOptionSubtext}>{nomeCompleto}</span>
                            )}
                          </div>
                        </label>
                      )
                    })
                  )}
                </div>
              </div>
            )}

            {usuariosSelecionados.length > 0 && (
              <div className={styles.selectedUsersPreview}>
                {usuariosSelecionados.map((item) => (
                  <span key={item.id} className={styles.userChip}>{obterNomeUsuario(item)}</span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className={styles.userViewer}>
            <span className={styles.selectorLabel}>Usuário</span>
            <div className={styles.userViewerCard}>{usuario?.nome_guerra || usuario?.nome || 'Usuário atual'}</div>
          </div>
        )}

        <div className={styles.summaryCards}>
          {isLoading ? (
            <>
              <Skeleton height={92} />
              <Skeleton height={92} />
              <Skeleton height={92} />
              <Skeleton height={92} />
            </>
          ) : (
            <>
              <Card padding="sm">
                <StatCard label="Lançado normal" value={resumoPeriodo.minutosNormais} suffix="min" variant="accent" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Hora extra lançada" value={resumoPeriodo.minutosExtras} suffix="min" variant="warning" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Capacidade do período" value={resumoPeriodo.minutosCapacidade} suffix="min" variant="default" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Ociosidade" value={resumoPeriodo.minutosOciosos} suffix="min" variant="default" size="sm" />
              </Card>
            </>
          )}
        </div>

        <div className={styles.legend}>
          <h4 className={styles.legendTitle}>Contexto exibido</h4>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorNormal}`} /><span>Lançamento normal</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorExtra}`} /><span>Hora extra</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorConsolidado}`} /><span>Consolidado</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorFeriado}`} /><span>Feriado</span></div>
          </div>
          {ehAdmin && (
            <p className={styles.renderHint}>
              Passe o mouse sobre o dia para ver a distribuição dos lançamentos por usuário. Clique no dia para abrir o detalhe e lançar ou editar atividades.
            </p>
          )}
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.calendarContainer}>
          <CalendarHeader
            view={calendar.view}
            periodLabel={calendar.periodLabel}
            onViewChange={calendar.setView}
            onPrev={calendar.goToPrev}
            onNext={calendar.goToNext}
            onToday={calendar.goToToday}
          />

          {isError ? (
            <div className={styles.errorState}><p>Não foi possível carregar a agenda realizada.</p></div>
          ) : (
            <CalendarGrid
              days={calendar.calendarDays}
              weekDays={calendar.weekDays}
              view={calendar.view}
              getDiaData={getDiaData}
              getHoverUsuarios={ehAdmin ? getHoverUsuarios : undefined}
              getCapacityDisplay={getCapacityDisplay}
              selectedDates={calendar.selectedDates}
              onSelectDate={calendar.selectDate}
              onSelectRange={calendar.selectRange}
              onDayClick={(date) => handleDayClick(date)}
              isAdmin={ehAdmin}
              loading={isLoading || agendasMultiplosUsuariosQuery.isLoading}
              exibirIndicadorOcioso
              hoverTitle="Lançamentos por usuário"
              exibirPlanejamento={false}
            />
          )}
        </div>
      </main>

      <DayDetailPanel
        open={detailPanelOpen}
        onClose={() => setDetailPanelOpen(false)}
        selectedDates={calendar.selectedDates}
        selectedRange={calendar.selectedRange}
        getDiaData={getDiaData}
        isAdmin={ehAdmin}
        onAddLancamento={handleAddLancamento}
        onEditLancamento={handleEditLancamento}
        onConsolidar={ehAdmin ? () => setConsolidacaoOpen(true) : undefined}
        exibirPlanejamento={false}
        tituloLancamentos="Atividades realizadas"
        podeAdicionarLancamento={(date, dia) => podeLancarNoDia(date, dia) && (!ehAdmin || idsUsuariosPainel.length === 1)}
      />

      <LancamentoForm
        open={lancamentoOpen}
        onClose={() => {
          setLancamentoOpen(false)
          setLancamentoEdicao(null)
          setLancamentoDate(null)
        }}
        date={lancamentoDate}
        lancamento={lancamentoEdicao}
        blocos={blocos}
        tiposAtividade={tiposAtividade}
        isAdmin={ehAdmin}
        usuarioId={ehAdmin ? usuarioIdPrincipal ?? null : null}
      />

      {ehAdmin && (
        <ConsolidacaoModal
          open={consolidacaoOpen}
          onClose={() => setConsolidacaoOpen(false)}
          dateRange={intervaloSelecionado}
          usuarioIds={idsUsuariosPainel}
        />
      )}
    </div>
  )
}
