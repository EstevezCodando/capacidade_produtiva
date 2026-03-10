// ============================================================
// AgendaPrevista — Página de planejamento de capacidade
// ============================================================
import { useState, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useCalendarNavigation, useAgendaData } from '@/hooks/useCalendar'
import CalendarHeader from '@/components/calendar/CalendarHeader'
import CalendarGrid from '@/components/calendar/CalendarGrid'
import DayDetailPanel from '@/components/agenda/DayDetailPanel'
import LancamentoForm from '@/components/agenda/LancamentoForm'
import ConsolidacaoModal from '@/components/agenda/ConsolidacaoModal'
import { Select, Card, StatCard, Skeleton } from '@/components/ui/Common'
import styles from './AgendaPage.module.css'

const MOCK_BLOCOS = [
  { id: 1, nome: 'Bloco A - Cartografia' },
  { id: 2, nome: 'Bloco B - Levantamento' },
  { id: 3, nome: 'Bloco C - Processamento' },
]

const MOCK_USUARIOS = [
  { id: 1, nome: 'João Silva', nome_guerra: 'Silva' },
  { id: 2, nome: 'Maria Santos', nome_guerra: 'Santos' },
  { id: 3, nome: 'Pedro Costa', nome_guerra: 'Costa' },
]

export default function AgendaPrevista() {
  const { ehAdmin, usuario } = useAuth()
  const [selectedUsuarioId, setSelectedUsuarioId] = useState<number | undefined>(undefined)
  const [detailPanelOpen, setDetailPanelOpen] = useState(false)
  const [lancamentoFormOpen, setLancamentoFormOpen] = useState(false)
  const [consolidacaoOpen, setConsolidacaoOpen] = useState(false)
  const [lancamentoDate, setLancamentoDate] = useState<Date | null>(null)

  const calendar = useCalendarNavigation({ initialView: 'month' })

  const usuarioIdParaCarregar = ehAdmin && selectedUsuarioId ? selectedUsuarioId : usuario?.usuario_id
  const { capacidade, getDiaData, isLoading, isError } = useAgendaData({
    usuarioId: usuarioIdParaCarregar,
    isAdmin: ehAdmin,
    dataInicio: calendar.formatForApi(calendar.dateRange.start),
    dataFim: calendar.formatForApi(calendar.dateRange.end),
    enabled: !!usuarioIdParaCarregar,
  })

  const handleDayClick = useCallback((date: Date) => {
    calendar.selectDate(date)
    setDetailPanelOpen(true)
  }, [calendar])

  const handleAddLancamento = useCallback((date: Date) => {
    setLancamentoDate(date)
    setLancamentoFormOpen(true)
  }, [])

  const handleAddPlanejamento = useCallback((date: Date) => {
    console.log('Add planejamento for', date)
  }, [])

  const handleConsolidar = useCallback(() => {
    setConsolidacaoOpen(true)
  }, [])

  const resumoPeriodo = capacidade?.resumo

  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2 className={styles.sidebarTitle}>Agenda Prevista</h2>
          <p className={styles.sidebarSubtitle}>Planejamento de capacidade</p>
        </div>

        {ehAdmin && (
          <div className={styles.userSelector}>
            <label className={styles.selectorLabel}>Usuário</label>
            <Select
              value={selectedUsuarioId?.toString() ?? ''}
              onChange={(v) => setSelectedUsuarioId(v ? parseInt(v, 10) : undefined)}
              options={[{ value: '', label: 'Selecione...' }, ...MOCK_USUARIOS.map((u) => ({ value: u.id.toString(), label: u.nome_guerra || u.nome }))]}
              size="md"
            />
          </div>
        )}

        <div className={styles.summaryCards}>
          {isLoading ? (
            <><Skeleton height={80} /><Skeleton height={80} /><Skeleton height={80} /></>
          ) : (
            <>
              <Card padding="sm"><StatCard label="Previsto Normal" value={resumoPeriodo?.minutos_previstos_normais ?? 0} suffix="min" variant="default" size="sm" /></Card>
              <Card padding="sm"><StatCard label="Realizado em Bloco" value={resumoPeriodo?.minutos_realizados_bloco_normais ?? 0} suffix="min" variant="accent" size="sm" /></Card>
              <Card padding="sm"><StatCard label="Horas Extras" value={resumoPeriodo?.minutos_extras_totais ?? 0} suffix="min" variant="warning" size="sm" /></Card>
              <Card padding="sm"><StatCard label="Ociosos" value={resumoPeriodo?.minutos_ociosos ?? 0} suffix="min" variant={resumoPeriodo?.minutos_ociosos ? 'error' : 'default'} size="sm" /></Card>
            </>
          )}
        </div>

        <div className={styles.legend}>
          <h4 className={styles.legendTitle}>Legenda</h4>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorNormal}`} /><span>Capacidade normal</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorExtra}`} /><span>Hora extra</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorConsolidado}`} /><span>Consolidado</span></div>
            <div className={styles.legendItem}><span className={`${styles.legendColor} ${styles.legendColorFeriado}`} /><span>Feriado</span></div>
          </div>
        </div>
      </aside>

      <main className={styles.main}>
        <CalendarHeader periodLabel={calendar.periodLabel} view={calendar.view} onViewChange={calendar.setView} onPrev={calendar.goToPrev} onNext={calendar.goToNext} onToday={calendar.goToToday} loading={isLoading} />
        <div className={styles.calendarContainer}>
          {isError ? (
            <div className={styles.errorState}><p>Erro ao carregar dados da agenda</p></div>
          ) : (
            <CalendarGrid days={calendar.calendarDays} weekDays={calendar.weekDays} view={calendar.view} getDiaData={getDiaData} selectedDates={calendar.selectedDates} onSelectDate={calendar.selectDate} onSelectRange={calendar.selectRange} onDayClick={handleDayClick} isAdmin={ehAdmin} loading={isLoading} />
          )}
        </div>
      </main>

      <DayDetailPanel open={detailPanelOpen} onClose={() => setDetailPanelOpen(false)} selectedDates={calendar.selectedDates} selectedRange={calendar.selectedRange} getDiaData={getDiaData} isAdmin={ehAdmin} onAddLancamento={handleAddLancamento} onAddPlanejamento={handleAddPlanejamento} onConsolidar={handleConsolidar} />
      <LancamentoForm open={lancamentoFormOpen} onClose={() => setLancamentoFormOpen(false)} date={lancamentoDate} blocos={MOCK_BLOCOS} />
      <ConsolidacaoModal open={consolidacaoOpen} onClose={() => setConsolidacaoOpen(false)} dateRange={calendar.selectedRange} usuarioIds={selectedUsuarioId ? [selectedUsuarioId] : []} />
    </div>
  )
}
