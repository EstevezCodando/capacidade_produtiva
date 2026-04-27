// ============================================================
// MinhaAgenda — Agenda realizada do próprio usuário
// ============================================================
import { useState, useCallback, useMemo } from 'react'
import { startOfToday } from 'date-fns'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { useCalendarNavigation, useAgendaData } from '@/hooks/useCalendar'
import CalendarHeader from '@/components/calendar/CalendarHeader'
import CalendarGrid from '@/components/calendar/CalendarGrid'
import DayDetailPanel from '@/components/agenda/DayDetailPanel'
import LancamentoForm from '@/components/agenda/LancamentoForm'
import { Card, StatCard, Skeleton, CapacityBar } from '@/components/ui/Common'
import { getBlocos } from '@/api/agenda'
import type { Lancamento } from '@/types/agenda'
import styles from '../AgendaRealizada/AgendaPage.module.css'

export default function MinhaAgenda() {
  const { usuario } = useAuth()
  const [detailPanelOpen, setDetailPanelOpen] = useState(false)
  const [lancamentoFormOpen, setLancamentoFormOpen] = useState(false)
  const [lancamentoDate, setLancamentoDate] = useState<Date | null>(null)
  const [lancamentoParaEditar, setLancamentoParaEditar] = useState<Lancamento | null>(null)

  const calendar = useCalendarNavigation({ initialView: 'month' })

  const { agenda, capacidade, getDiaData, isLoading, isError } = useAgendaData({
    usuarioId: usuario?.usuario_id,
    isAdmin: false,
    dataInicio: calendar.formatForApi(calendar.dateRange.start),
    dataFim: calendar.formatForApi(calendar.dateRange.end),
    enabled: !!usuario?.usuario_id,
  })

  const blocosQuery = useQuery({
    queryKey: ['blocos'],
    queryFn: getBlocos,
    staleTime: 5 * 60 * 1000,
  })

  // Mapa lancamento.id → Lancamento completo (para edição)
  const lancamentosMap = useMemo(() => {
    const map = new Map<number, Lancamento>()
    const userId = usuario?.usuario_id ?? 0
    for (const dia of agenda?.dias ?? []) {
      for (const ap of dia.lancamentos) {
        map.set(ap.id, {
          id: ap.id,
          usuario_id: userId,
          data_lancamento: ap.data,
          bloco_id: ap.bloco_id,
          tipo_atividade_id: ap.tipo_atividade_id,
          tipo_atividade_codigo: ap.tipo_atividade,
          tipo_atividade_nome: ap.tipo_atividade_nome,
          tipo_atividade_cor: ap.tipo_atividade_cor,
          faixa_minuto: ap.faixa,
          minutos: ap.minutos,
          descricao: null,
          criado_por: userId,
          atualizado_por: null,
          criado_em: ap.data,
          atualizado_em: ap.data,
        })
      }
    }
    return map
  }, [agenda, usuario?.usuario_id])

  const handleDayClick = useCallback((date: Date) => {
    calendar.selectDate(date)
    setDetailPanelOpen(true)
  }, [calendar])

  const handleAddLancamento = useCallback((date: Date) => {
    setLancamentoParaEditar(null)
    setLancamentoDate(date)
    setLancamentoFormOpen(true)
  }, [])

  const handleEditLancamento = useCallback((id: number) => {
    const lanc = lancamentosMap.get(id)
    if (!lanc) return
    setLancamentoParaEditar(lanc)
    setLancamentoDate(new Date(lanc.data_lancamento + 'T12:00:00'))
    setLancamentoFormOpen(true)
  }, [lancamentosMap])

  const resumoPeriodo = capacidade?.resumo
  const totalNormal = resumoPeriodo
    ? resumoPeriodo.minutos_realizados_bloco_normais + resumoPeriodo.minutos_perdidos_externas_normais
    : 0
  const capacidadeNormal = resumoPeriodo?.minutos_previstos_normais ?? 360
  const blocos = blocosQuery.data?.map((b) => ({ id: b.id, nome: b.nome })) ?? []

  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2 className={styles.sidebarTitle}>Minha Agenda</h2>
          <p className={styles.sidebarSubtitle}>Lançamentos e apontamentos</p>
        </div>

        <div className={styles.capacitySection}>
          <h4 className={styles.sectionTitle}>Utilização do Período</h4>
          {isLoading ? (
            <Skeleton height={60} />
          ) : (
            <CapacityBar
              normalValue={totalNormal}
              normalMax={capacidadeNormal}
              extraValue={resumoPeriodo?.minutos_extras_totais ?? 0}
              extraMax={240}
              size="lg"
            />
          )}
        </div>

        <div className={styles.summaryCards}>
          {isLoading ? (
            <><Skeleton height={70} /><Skeleton height={70} /><Skeleton height={70} /><Skeleton height={70} /></>
          ) : (
            <>
              <Card padding="sm">
                <StatCard label="Realizado em Bloco" value={resumoPeriodo?.minutos_realizados_bloco_normais ?? 0} suffix="min" variant="accent" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Atividades Externas" value={resumoPeriodo?.minutos_perdidos_externas_normais ?? 0} suffix="min" variant="default" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Hora Extra" value={resumoPeriodo?.minutos_extras_totais ?? 0} suffix="min" variant="warning" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Não Alocados" value={resumoPeriodo?.minutos_nao_alocados ?? 0} suffix="min" variant="default" size="sm" />
              </Card>
              <Card padding="sm">
                <StatCard label="Ociosos" value={resumoPeriodo?.minutos_ociosos ?? 0} suffix="min" variant={resumoPeriodo?.minutos_ociosos ? 'error' : 'default'} size="sm" />
              </Card>
            </>
          )}
        </div>

        <div className={styles.legend}>
          <h4 className={styles.legendTitle}>Legenda</h4>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorNormal}`} /><span>Normal utilizado</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorExtra}`} /><span>Hora extra</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorConsolidado}`} /><span>Consolidado</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorFeriado}`} /><span>Feriado</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorIndisponivel}`} /><span>Indisponível</span></div>
          </div>
        </div>
      </aside>

      <main className={styles.main}>
        <CalendarHeader
          periodLabel={calendar.periodLabel}
          onPrev={calendar.goToPrev}
          onNext={calendar.goToNext}
          onToday={calendar.goToToday}
          loading={isLoading}
        />
        <div className={styles.calendarContainer}>
          {isError ? (
            <div className={styles.errorState}><p>Erro ao carregar dados da agenda</p></div>
          ) : (
            <CalendarGrid
              days={calendar.calendarDays}
              weekDays={calendar.weekDays}
              view={calendar.view}
              getDiaData={getDiaData}
              selectedDates={calendar.selectedDates}
              onSelectDate={calendar.selectDate}
              onSelectRange={calendar.selectRange}
              onDayClick={handleDayClick}
              isAdmin={false}
              loading={isLoading}
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
        isAdmin={false}
        maxDate={startOfToday()}
        onAddLancamento={handleAddLancamento}
        onEditLancamento={handleEditLancamento}
      />
      <LancamentoForm
        open={lancamentoFormOpen}
        onClose={() => setLancamentoFormOpen(false)}
        date={lancamentoDate}
        lancamento={lancamentoParaEditar}
        blocos={blocos}
      />
    </div>
  )
}
