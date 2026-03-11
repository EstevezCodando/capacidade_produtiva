import { useEffect, useMemo, useRef, useState } from 'react'
import { format } from 'date-fns'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { useCalendarNavigation, useAgendaData } from '@/hooks/useCalendar'
import { consolidarPeriodo, criarPlanejamento, getConfigTeto, getTiposAtividade, getUsuarios } from '@/api/agenda'
import CalendarHeader from '@/components/calendar/CalendarHeader'
import CalendarGrid from '@/components/calendar/CalendarGrid'
import ConsolidacaoModal from '@/components/agenda/ConsolidacaoModal'
import Modal from '@/components/ui/Modal'
import { Button, Card, Input, Select, Skeleton, StatCard, Textarea } from '@/components/ui/Common'
import type { PlanejamentoInput, TipoAtividade, UsuarioResumo } from '@/types/agenda'
import styles from './AgendaPage.module.css'

interface FormularioPlanejamento {
  tipoAtividadeId: string
  tipoHorario: 'NORMAL' | 'EXTRA'
  unidadeTempo: 'HORAS' | 'MINUTOS'
  quantidade: string
  descricao: string
}

const ESTADO_INICIAL_FORM: FormularioPlanejamento = {
  tipoAtividadeId: '',
  tipoHorario: 'NORMAL',
  unidadeTempo: 'HORAS',
  quantidade: '1',
  descricao: '',
}

function obterNomeUsuario(usuario: UsuarioResumo): string {
  return usuario.nome_guerra?.trim() || usuario.nome
}

function formatarHorasMinutos(minutos: number): string {
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  if (horas > 0 && resto > 0) return `${horas}h ${resto}min`
  if (horas > 0) return `${horas}h`
  return `${resto}min`
}

export default function AgendaPrevista() {
  const queryClient = useQueryClient()
  const { ehAdmin, usuario } = useAuth()
  const calendar = useCalendarNavigation({ initialView: 'month' })

  const [selectedUsuarioIds, setSelectedUsuarioIds] = useState<number[]>([])
  const [usuariosOpen, setUsuariosOpen] = useState(false)
  const [planejamentoOpen, setPlanejamentoOpen] = useState(false)
  const [consolidacaoOpen, setConsolidacaoOpen] = useState(false)
  const [filtroUsuarios, setFiltroUsuarios] = useState('')
  const [form, setForm] = useState<FormularioPlanejamento>(ESTADO_INICIAL_FORM)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const dropdownRef = useRef<HTMLDivElement | null>(null)

  const { data: usuarios = [], isLoading: loadingUsuarios } = useQuery({
    queryKey: ['usuarios'],
    queryFn: getUsuarios,
    enabled: ehAdmin,
    staleTime: 60_000,
  })

  const { data: tiposAtividadeResposta, isLoading: loadingTipos } = useQuery({
    queryKey: ['tipos-atividade'],
    queryFn: getTiposAtividade,
    staleTime: 60_000,
  })

  const { data: configTeto } = useQuery({
    queryKey: ['config-teto'],
    queryFn: getConfigTeto,
    staleTime: 60_000,
  })

  const tiposAtividade: TipoAtividade[] = useMemo(() => {
    if (Array.isArray(tiposAtividadeResposta)) return tiposAtividadeResposta as TipoAtividade[]
    if (tiposAtividadeResposta && Array.isArray((tiposAtividadeResposta as { tipos?: TipoAtividade[] }).tipos)) {
      return (tiposAtividadeResposta as { tipos: TipoAtividade[] }).tipos
    }
    return []
  }, [tiposAtividadeResposta])

  const usuarioIdPrincipal = useMemo(() => {
    if (!ehAdmin) return usuario?.usuario_id
    if (selectedUsuarioIds.length > 0) return selectedUsuarioIds[0]
    return usuario?.usuario_id
  }, [ehAdmin, selectedUsuarioIds, usuario?.usuario_id])

  const { capacidade, getDiaData, isLoading, isError, invalidate } = useAgendaData({
    usuarioId: usuarioIdPrincipal,
    isAdmin: ehAdmin,
    dataInicio: calendar.formatForApi(calendar.dateRange.start),
    dataFim: calendar.formatForApi(calendar.dateRange.end),
    enabled: !!usuarioIdPrincipal,
  })

  const resumoPeriodo = capacidade?.resumo
  const capacidadePadraoMinutos = configTeto?.teto_normal_min ?? 360
  const diasSelecionados = calendar.selectedDates.length
  const intervaloSelecionado = useMemo(() => {
    if (calendar.selectedRange) return calendar.selectedRange
    if (calendar.selectedDates.length === 1) {
      return { start: calendar.selectedDates[0], end: calendar.selectedDates[0] }
    }
    return null
  }, [calendar.selectedDates, calendar.selectedRange])
  const podeCriarPlanejamento = ehAdmin && selectedUsuarioIds.length > 0 && diasSelecionados >= 1
  const podeConsolidar = !!intervaloSelecionado && diasSelecionados >= 2

  const usuariosSelecionados = useMemo(
    () => usuarios.filter((item) => selectedUsuarioIds.includes(item.id)),
    [usuarios, selectedUsuarioIds],
  )

  const usuariosFiltrados = useMemo(() => {
    const termo = filtroUsuarios.trim().toLowerCase()
    if (!termo) return usuarios
    return usuarios.filter((item) => {
      const nome = obterNomeUsuario(item).toLowerCase()
      const nomeCompleto = item.nome.toLowerCase()
      return nome.includes(termo) || nomeCompleto.includes(termo)
    })
  }, [filtroUsuarios, usuarios])

  const usuarioPrincipal = useMemo(
    () => usuarios.find((item) => item.id === usuarioIdPrincipal),
    [usuarios, usuarioIdPrincipal],
  )

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

  const criarPlanejamentoMutation = useMutation({
    mutationFn: async () => {
      const novosErros: Record<string, string> = {}
      const quantidade = Number(form.quantidade)
      const minutosCalculados = form.unidadeTempo === 'HORAS' ? quantidade * 60 : quantidade

      if (!form.tipoAtividadeId) novosErros.tipoAtividadeId = 'Selecione um tipo de atividade.'
      if (!form.tipoHorario) novosErros.tipoHorario = 'Selecione o tipo de horário.'
      if (!Number.isFinite(quantidade) || quantidade <= 0) novosErros.quantidade = 'Informe uma quantidade válida.'
      if (calendar.selectedDates.length === 0) novosErros.periodo = 'Selecione pelo menos um dia.'
      if (selectedUsuarioIds.length === 0) novosErros.usuarios = 'Selecione ao menos um usuário.'

      setErrors(novosErros)
      if (Object.keys(novosErros).length > 0) {
        throw new Error('Existem campos obrigatórios pendentes.')
      }

      const dias = calendar.selectedDates.map((data) => format(data, 'yyyy-MM-dd'))
      const descricaoComTipo = (() => {
        const tipoSelecionado = tiposAtividade.find((item) => item.id === Number(form.tipoAtividadeId))
        const partes = []
        if (tipoSelecionado?.nome) partes.push(`[${tipoSelecionado.nome}]`)
        if (form.descricao.trim()) partes.push(form.descricao.trim())
        return partes.join(' ')
      })()

      const lancamentos: PlanejamentoInput[] = []
      for (const usuarioId of selectedUsuarioIds) {
        for (const data of dias) {
          lancamentos.push({
            usuario_id: usuarioId,
            data,
            bloco_id: null,
            minutos_planejados_normais: form.tipoHorario === 'NORMAL' ? minutosCalculados : 0,
            minutos_planejados_extras: form.tipoHorario === 'EXTRA' ? minutosCalculados : 0,
            descricao: descricaoComTipo || undefined,
          })
        }
      }

      await Promise.all(lancamentos.map((item) => criarPlanejamento(item)))
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agenda'] })
      await queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      invalidate()
      setPlanejamentoOpen(false)
      setForm(ESTADO_INICIAL_FORM)
      setErrors({})
    },
    onError: (error) => {
      setErrors((atual) => ({
        ...atual,
        submit: error instanceof Error ? error.message : 'Não foi possível criar o planejamento.',
      }))
    },
  })

  const consolidacaoCsvMutation = useMutation({
    mutationFn: async () => {
      if (!intervaloSelecionado) throw new Error('Selecione um período para consolidar.')
      return consolidarPeriodo({
        data_inicio: format(intervaloSelecionado.start, 'yyyy-MM-dd'),
        data_fim: format(intervaloSelecionado.end, 'yyyy-MM-dd'),
        usuarios_ids: selectedUsuarioIds.length > 0 ? selectedUsuarioIds : undefined,
        ignorar_pendencias: false,
      })
    },
    onSuccess: (resultado) => {
      if (!resultado.pendencias.length) return
      const linhas = [
        ['usuario', 'dia', 'horas_faltantes'].join(','),
        ...resultado.pendencias.map((pendencia) => [
          JSON.stringify(pendencia.usuario_nome ?? `Usuário ${pendencia.usuario_id}`),
          pendencia.data,
          JSON.stringify(pendencia.motivo),
        ].join(',')),
      ]
      const blob = new Blob([linhas.join('
')], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `pendencias-consolidacao-${format(new Date(), 'yyyyMMdd-HHmmss')}.csv`
      link.click()
      URL.revokeObjectURL(url)
    },
  })

  function alternarUsuario(usuarioId: number) {
    setSelectedUsuarioIds((atual) => {
      if (atual.includes(usuarioId)) return atual.filter((id) => id !== usuarioId)
      return [...atual, usuarioId].sort((a, b) => a - b)
    })
  }

  function abrirPlanejamento() {
    setErrors({})
    setPlanejamentoOpen(true)
  }

  function resumoUsuariosSelecionados(): string {
    if (!selectedUsuarioIds.length) return 'Selecione os usuários'
    if (usuariosSelecionados.length <= 2) return usuariosSelecionados.map(obterNomeUsuario).join(', ')
    return `${usuariosSelecionados.length} usuários selecionados`
  }

  const intervaloSelecionadoLabel = (() => {
    if (!intervaloSelecionado) return 'Nenhum dia selecionado'
    if (format(intervaloSelecionado.start, 'yyyy-MM-dd') === format(intervaloSelecionado.end, 'yyyy-MM-dd')) {
      return format(intervaloSelecionado.start, 'dd/MM/yyyy')
    }
    return `${format(intervaloSelecionado.start, 'dd/MM/yyyy')} até ${format(intervaloSelecionado.end, 'dd/MM/yyyy')}`
  })()

  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2 className={styles.sidebarTitle}>Agenda Prevista</h2>
          <p className={styles.sidebarSubtitle}>Planejamento operacional com dados reais</p>
        </div>

        {ehAdmin ? (
          <div className={styles.userSelector} ref={dropdownRef}>
            <label className={styles.selectorLabel}>Usuários</label>
            <button type="button" className={styles.userDropdownTrigger} onClick={() => setUsuariosOpen((valor) => !valor)}>
              <div className={styles.userDropdownTriggerText}>
                <span className={styles.userDropdownTitle}>{resumoUsuariosSelecionados()}</span>
                <span className={styles.userDropdownHint}>Seleção em lote para o planejamento</span>
              </div>
              <span className={styles.userDropdownMeta}>{selectedUsuarioIds.length}</span>
            </button>
            {usuariosSelecionados.length > 0 && (
              <div className={styles.selectedUsersPreview}>
                {usuariosSelecionados.slice(0, 4).map((item) => (
                  <span key={item.id} className={styles.userChip}>{obterNomeUsuario(item)}</span>
                ))}
                {usuariosSelecionados.length > 4 && <span className={styles.userChip}>+{usuariosSelecionados.length - 4}</span>}
              </div>
            )}
            {usuariosOpen && (
              <div className={styles.userDropdownMenu}>
                <Input
                  value={filtroUsuarios}
                  onChange={(evento) => setFiltroUsuarios(evento.target.value)}
                  placeholder="Buscar usuário"
                  className={styles.userSearchInput}
                />
                <div className={styles.userDropdownList}>
                  {loadingUsuarios ? (
                    <div className={styles.userDropdownLoading}>Carregando usuários...</div>
                  ) : usuariosFiltrados.length === 0 ? (
                    <div className={styles.userDropdownLoading}>Nenhum usuário encontrado.</div>
                  ) : (
                    usuariosFiltrados.map((item) => {
                      const marcado = selectedUsuarioIds.includes(item.id)
                      return (
                        <label key={item.id} className={styles.userOption}>
                          <input type="checkbox" checked={marcado} onChange={() => alternarUsuario(item.id)} />
                          <span className={styles.userOptionText}>{obterNomeUsuario(item)}</span>
                        </label>
                      )
                    })
                  )}
                </div>
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
              <Skeleton height={88} />
              <Skeleton height={88} />
              <Skeleton height={88} />
            </>
          ) : (
            <>
              <Card padding="sm"><StatCard label="Previsto normal" value={resumoPeriodo?.minutos_previstos_normais ?? 0} suffix="min" variant="default" size="sm" /></Card>
              <Card padding="sm"><StatCard label="Realizado em bloco" value={resumoPeriodo?.minutos_realizados_bloco_normais ?? 0} suffix="min" variant="accent" size="sm" /></Card>
              <Card padding="sm"><StatCard label="Horas extras" value={resumoPeriodo?.minutos_extras_totais ?? 0} suffix="min" variant="warning" size="sm" /></Card>
              <Card padding="sm"><StatCard label="Capacidade diária" value={formatarHorasMinutos(capacidadePadraoMinutos)} variant="default" size="sm" /></Card>
            </>
          )}
        </div>

        <div className={styles.legend}>
          <h4 className={styles.legendTitle}>Contexto exibido</h4>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorNormal}`} /><span>Capacidade normal</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorExtra}`} /><span>Hora extra</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorConsolidado}`} /><span>Consolidado</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorFeriado}`} /><span>Feriado</span></div>
          </div>
          {ehAdmin && usuarioPrincipal && (
            <p className={styles.renderHint}>A agenda renderizada usa {obterNomeUsuario(usuarioPrincipal)} como referência visual. O lançamento continua sendo aplicado a todos os usuários selecionados.</p>
          )}
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.topActionsBar}>
          <div>
            <h3 className={styles.topActionsTitle}>Planejamento do período</h3>
            <p className={styles.topActionsSubtitle}>Selecione um dia ou um intervalo. O calendário permanece renderizado mesmo quando o administrador trabalha com vários usuários.</p>
          </div>
          {ehAdmin && (
            <div className={styles.topActionsButtons}>
              <Button variant="secondary" onClick={() => { setConsolidacaoOpen(true); void consolidacaoCsvMutation.mutateAsync().catch(() => undefined) }} disabled={!podeConsolidar}>
                Consolidar período
              </Button>
              <Button variant="primary" onClick={abrirPlanejamento} disabled={!podeCriarPlanejamento}>
                Criar planejamento
              </Button>
            </div>
          )}
        </div>

        <div className={styles.selectionSummary}>
          <div className={styles.selectionPill}><strong>Período</strong><span>{intervaloSelecionadoLabel}</span></div>
          <div className={styles.selectionPill}><strong>Dias</strong><span>{diasSelecionados}</span></div>
          {ehAdmin && <div className={styles.selectionPill}><strong>Usuários</strong><span>{selectedUsuarioIds.length}</span></div>}
        </div>

        <CalendarHeader
          periodLabel={calendar.periodLabel}
          view={calendar.view}
          onViewChange={calendar.setView}
          onPrev={calendar.goToPrev}
          onNext={calendar.goToNext}
          onToday={calendar.goToToday}
          loading={isLoading}
        />

        <div className={styles.calendarContainer}>
          {isError ? (
            <div className={styles.errorState}><p>Erro ao carregar dados da agenda.</p></div>
          ) : (
            <CalendarGrid
              days={calendar.calendarDays}
              weekDays={calendar.weekDays}
              view={calendar.view}
              getDiaData={getDiaData}
              selectedDates={calendar.selectedDates}
              onSelectDate={calendar.selectDate}
              onSelectRange={calendar.selectRange}
              onDayClick={(date) => calendar.selectDate(date)}
              isAdmin={ehAdmin}
              loading={isLoading}
            />
          )}
        </div>
      </main>

      <Modal open={planejamentoOpen} onClose={() => setPlanejamentoOpen(false)} title="Criar planejamento" size="xl">
        <form className={styles.planejamentoForm} onSubmit={(evento) => { evento.preventDefault(); criarPlanejamentoMutation.mutate() }}>
          <section className={styles.modalSection}>
            <div className={styles.modalSectionHeader}>
              <h4 className={styles.modalSectionTitle}>Resumo do lançamento</h4>
              <p className={styles.modalSectionSubtitle}>Confira período, volume e usuários antes de salvar.</p>
            </div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>Período</span><strong>{intervaloSelecionadoLabel}</strong></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>Dias</span><strong>{diasSelecionados}</strong></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>Usuários</span><strong>{selectedUsuarioIds.length}</strong></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>Carga por dia</span><strong>{formatarHorasMinutos(capacidadePadraoMinutos)}</strong></div>
            </div>
            <div className={styles.chipsWrap}>
              {usuariosSelecionados.map((item) => (
                <span key={item.id} className={styles.userChip}>{obterNomeUsuario(item)}</span>
              ))}
            </div>
          </section>

          <section className={styles.modalSection}>
            <div className={styles.modalSectionHeader}>
              <h4 className={styles.modalSectionTitle}>Configuração da atividade</h4>
              <p className={styles.modalSectionSubtitle}>Defina o tipo, a faixa de horário e a carga de tempo.</p>
            </div>
            <div className={styles.formGrid}>
              <div className={styles.formField}>
                <label className={styles.formLabel}>Tipo de atividade</label>
                <Select
                  value={form.tipoAtividadeId}
                  onChange={(valor) => setForm((atual) => ({ ...atual, tipoAtividadeId: valor }))}
                  options={tiposAtividade.map((tipo) => ({ value: String(tipo.id), label: tipo.nome }))}
                  placeholder={loadingTipos ? 'Carregando...' : 'Selecione'}
                />
                {errors.tipoAtividadeId && <span className={styles.formError}>{errors.tipoAtividadeId}</span>}
              </div>
              <div className={styles.formField}>
                <label className={styles.formLabel}>Tipo de horário</label>
                <Select
                  value={form.tipoHorario}
                  onChange={(valor) => setForm((atual) => ({ ...atual, tipoHorario: valor as 'NORMAL' | 'EXTRA' }))}
                  options={[{ value: 'NORMAL', label: 'Normal' }, { value: 'EXTRA', label: 'Hora extra' }]}
                />
                {errors.tipoHorario && <span className={styles.formError}>{errors.tipoHorario}</span>}
              </div>
              <div className={styles.formField}>
                <label className={styles.formLabel}>Unidade do tempo</label>
                <Select
                  value={form.unidadeTempo}
                  onChange={(valor) => setForm((atual) => ({ ...atual, unidadeTempo: valor as 'HORAS' | 'MINUTOS' }))}
                  options={[{ value: 'HORAS', label: 'Horas' }, { value: 'MINUTOS', label: 'Minutos' }]}
                />
              </div>
              <div className={styles.formField}>
                <Input
                  label="Quantidade"
                  type="number"
                  min="1"
                  step="1"
                  value={form.quantidade}
                  onChange={(evento) => setForm((atual) => ({ ...atual, quantidade: evento.target.value }))}
                  error={errors.quantidade}
                />
              </div>
            </div>
          </section>

          <section className={styles.modalSection}>
            <div className={styles.modalSectionHeader}>
              <h4 className={styles.modalSectionTitle}>Descrição</h4>
              <p className={styles.modalSectionSubtitle}>Adicione contexto para facilitar o entendimento do planejamento.</p>
            </div>
            <Textarea
              label="Descrição opcional"
              rows={5}
              value={form.descricao}
              onChange={(evento) => setForm((atual) => ({ ...atual, descricao: evento.target.value }))}
              placeholder="Ex.: apoio ao processamento, afastamento, treinamento interno, atividade administrativa"
            />
          </section>

          {(errors.submit || errors.usuarios || errors.periodo) && (
            <div className={styles.submitError}>{errors.submit || errors.usuarios || errors.periodo}</div>
          )}

          <Modal.Footer>
            <Button type="button" variant="ghost" onClick={() => setPlanejamentoOpen(false)}>Cancelar</Button>
            <Button type="submit" variant="primary" loading={criarPlanejamentoMutation.isPending}>Criar lançamento</Button>
          </Modal.Footer>
        </form>
      </Modal>

      <ConsolidacaoModal
        open={consolidacaoOpen}
        onClose={() => setConsolidacaoOpen(false)}
        dateRange={intervaloSelecionado}
        usuarioIds={selectedUsuarioIds}
      />
    </div>
  )
}
