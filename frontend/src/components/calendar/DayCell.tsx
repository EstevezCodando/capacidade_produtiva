// ============================================================
// DayCell — Célula individual do calendário
// Mostra status, capacidade e indicadores visuais do dia
// ============================================================
import { useMemo } from 'react'
import { format } from 'date-fns'
import type { CalendarDay, DiaDaAgenda } from '@/types/agenda'
import styles from './Calendar.module.css'

interface HoverUsuarioResumo {
  usuarioId: number
  nome: string
  minutosPlanejados: number
  capacidadeMaxima: number
}

interface DayCellProps {
  calendarDay: CalendarDay
  diaData?: DiaDaAgenda
  hoverUsuarios?: HoverUsuarioResumo[]
  isSelected: boolean
  isInDragRange: boolean
  isAdmin?: boolean
  loading?: boolean
  onMouseDown: (e: React.MouseEvent) => void
  onMouseEnter: () => void
  onClick: () => void
}

function formatarHorasMinutos(minutos: number): string {
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  if (horas > 0 && resto > 0) return `${horas}h ${resto}min`
  if (horas > 0) return `${horas}h`
  return `${resto}min`
}

export default function DayCell({
  calendarDay,
  diaData,
  hoverUsuarios = [],
  isSelected,
  isInDragRange,
  isAdmin = false,
  loading = false,
  onMouseDown,
  onMouseEnter,
  onClick,
}: DayCellProps) {
  const { date, isCurrentMonth, isToday, isWeekend } = calendarDay

  const cellClasses = useMemo(() => {
    const classes = [styles.dayCell]

    if (!isCurrentMonth) classes.push(styles.dayCellOtherMonth)
    if (isToday) classes.push(styles.dayCellToday)
    if (isWeekend) classes.push(styles.dayCellWeekend)
    if (isSelected) classes.push(styles.dayCellSelected)
    if (isInDragRange && !isSelected) classes.push(styles.dayCellDragRange)
    if (loading) classes.push(styles.dayCellLoading)

    if (diaData) {
      if (diaData.eh_feriado) classes.push(styles.dayCellHoliday)
      if (diaData.eh_indisponivel) classes.push(styles.dayCellUnavailable)
      if (diaData.status === 'CONSOLIDADO') classes.push(styles.dayCellConsolidated)
    }

    return classes.join(' ')
  }, [isCurrentMonth, isToday, isWeekend, isSelected, isInDragRange, loading, diaData])

  const capacityInfo = useMemo(() => {
    if (!diaData) return null

    const normalUsed = diaData.apontado_normal_min
    const normalMax = diaData.teto_normal_min
    const extraUsed = diaData.apontado_extra_min
    const extraMax = diaData.teto_extra_min
    const planejadoTotal = diaData.planejamento.reduce(
      (sum, p) => sum + p.minutos_planejados_normais + p.minutos_planejados_extras,
      0,
    )

    const normalPct = normalMax > 0 ? Math.min(100, (normalUsed / normalMax) * 100) : 0
    const extraPct = extraMax > 0 ? Math.min(100, (extraUsed / extraMax) * 100) : 0

    let status: 'empty' | 'partial' | 'complete' | 'overtime' = 'empty'
    if (extraUsed > 0) status = 'overtime'
    else if (normalUsed >= normalMax) status = 'complete'
    else if (normalUsed > 0) status = 'partial'

    return {
      normalUsed,
      normalMax,
      extraUsed,
      extraMax,
      planejadoTotal,
      normalPct,
      extraPct,
      status,
      hasOcioso: diaData.minutos_ociosos > 0,
    }
  }, [diaData])

  const badges = useMemo(() => {
    const items: { key: string; label: string; variant: string }[] = []

    if (diaData?.eh_feriado) {
      items.push({ key: 'holiday', label: 'Feriado', variant: 'holiday' })
    }
    if (diaData?.eh_indisponivel) {
      const tipoLabel = {
        FERIAS: 'Férias',
        LICENCA: 'Licença',
        CURSO: 'Curso',
        AFASTAMENTO: 'Afastamento',
      }[diaData.tipo_indisponibilidade ?? 'AFASTAMENTO'] ?? 'Indisponível'
      items.push({ key: 'unavailable', label: tipoLabel, variant: 'unavailable' })
    }
    if (diaData?.status === 'CONSOLIDADO') {
      items.push({ key: 'consolidated', label: 'Consolidado', variant: 'consolidated' })
    }

    return items
  }, [diaData])

  return (
    <div
      className={cellClasses}
      onMouseDown={onMouseDown}
      onMouseEnter={onMouseEnter}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`${format(date, 'EEEE, d MMMM')}`}
    >
      <div className={styles.dayNumber}>
        <span className={styles.dayNumberText}>{format(date, 'd')}</span>
        {isToday && <span className={styles.todayIndicator} />}
      </div>

      {diaData && !loading && (
        <div className={styles.dayContent}>
          {badges.length > 0 && (
            <div className={styles.dayBadges}>
              {badges.map((badge) => (
                <span
                  key={badge.key}
                  className={`${styles.dayBadge} ${styles[`dayBadge-${badge.variant}`]}`}
                >
                  {badge.label}
                </span>
              ))}
            </div>
          )}

          {capacityInfo && !diaData.eh_feriado && !diaData.eh_indisponivel && (
            <div className={styles.dayCapacity}>
              <div className={styles.miniCapacityBar}>
                <div
                  className={`${styles.miniCapacityFill} ${styles[`miniCapacity-${capacityInfo.status}`]}`}
                  style={{ width: `${capacityInfo.normalPct}%` }}
                />
                {capacityInfo.extraUsed > 0 && (
                  <div
                    className={styles.miniCapacityExtra}
                    style={{ width: `${capacityInfo.extraPct}%` }}
                  />
                )}
              </div>
              <span className={styles.miniCapacityLabel}>
                {capacityInfo.normalUsed}
                {capacityInfo.extraUsed > 0 && (
                  <span className={styles.miniCapacityExtraLabel}>
                    +{capacityInfo.extraUsed}
                  </span>
                )}
              </span>
            </div>
          )}

          {diaData.planejamento.length > 0 && (
            <div className={styles.dayPlanejamento}>
              <span className={styles.planejamentoIcon}>◈</span>
              <span className={styles.planejamentoCount}>
                {capacityInfo?.planejadoTotal}min
              </span>
            </div>
          )}

          {diaData.lancamentos.length > 0 && (
            <div className={styles.dayLancamentos}>
              <span className={styles.lancamentosCount}>
                {diaData.lancamentos.length} lanç.
              </span>
            </div>
          )}
        </div>
      )}

      {hoverUsuarios.length > 0 && (
        <div className={styles.dayHoverCard}>
          <div className={styles.dayHoverTitle}>Carga planejada por usuário</div>
          <div className={styles.dayHoverList}>
            {hoverUsuarios.map((item) => {
              const percentual = item.capacidadeMaxima > 0
                ? Math.min(100, (item.minutosPlanejados / item.capacidadeMaxima) * 100)
                : 0
              return (
                <div key={`${item.usuarioId}-${format(date, 'yyyy-MM-dd')}`} className={styles.dayHoverItem}>
                  <div className={styles.dayHoverHeader}>
                    <span className={styles.dayHoverUser}>{item.nome}</span>
                    <span className={styles.dayHoverValue}>{formatarHorasMinutos(item.minutosPlanejados)} / {formatarHorasMinutos(item.capacidadeMaxima)}</span>
                  </div>
                  <div className={styles.dayHoverTrack}>
                    <div className={styles.dayHoverFill} style={{ width: `${percentual}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
          {isAdmin && <div className={styles.dayHoverHint}>Clique para abrir o detalhamento do dia.</div>}
        </div>
      )}

      {loading && (
        <div className={styles.daySkeleton}>
          <div className={styles.skeletonBar} />
          <div className={styles.skeletonBar} style={{ width: '60%' }} />
        </div>
      )}

      {capacityInfo?.hasOcioso && diaData?.status === 'ABERTO' && (
        <div className={styles.ociosoIndicator} title={`${diaData.minutos_ociosos}min ociosos`}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
        </div>
      )}
    </div>
  )
}
