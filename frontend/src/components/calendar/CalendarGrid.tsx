// ============================================================
// CalendarGrid — Grid de calendário mensal/semanal
// ============================================================
import { useMemo, useState, useCallback, useRef } from 'react'
import { format, isSameDay } from 'date-fns'
import type { CalendarDay, DiaDaAgenda, CalendarView } from '@/types/agenda'
import DayCell from './DayCell'
import styles from './Calendar.module.css'

interface SegmentoBarra {
  cor: string
  percentual: number
  minutos: number
}

interface HoverUsuarioResumo {
  usuarioId: number
  nome: string
  minutosPlanejados: number
  capacidadeMaxima: number
  segmentos?: SegmentoBarra[]
}

interface CapacityDisplay {
  totalMinutos: number
  totalExtraMinutos?: number
  segmentos: SegmentoBarra[]
}

interface CalendarGridProps {
  days: CalendarDay[]
  weekDays: { short: string; full: string }[]
  view: CalendarView
  getDiaData: (date: Date) => DiaDaAgenda | undefined
  getHoverUsuarios?: (date: Date) => HoverUsuarioResumo[]
  getCapacityDisplay?: (date: Date) => CapacityDisplay | null
  selectedDates: Date[]
  onSelectDate: (date: Date, addToSelection?: boolean) => void
  onSelectRange: (start: Date, end: Date) => void
  onDayClick: (date: Date, data?: DiaDaAgenda) => void
  isAdmin?: boolean
  loading?: boolean
  exibirIndicadorOcioso?: boolean
}

export default function CalendarGrid({
  days,
  weekDays,
  view,
  getDiaData,
  getHoverUsuarios,
  getCapacityDisplay,
  selectedDates,
  onSelectDate,
  onSelectRange,
  onDayClick,
  isAdmin = false,
  loading = false,
  exibirIndicadorOcioso = true,
}: CalendarGridProps) {
  const [dragStart, setDragStart] = useState<Date | null>(null)
  const [dragEnd, setDragEnd] = useState<Date | null>(null)
  const isDragging = useRef(false)

  const visibleDays = useMemo(() => {
    if (view === 'month') return days
    if (view === 'week') return days.slice(0, 7)
    return days.slice(0, 1)
  }, [days, view])

  const handleMouseDown = useCallback((date: Date, e: React.MouseEvent) => {
    if (e.button !== 0) return
    isDragging.current = true
    setDragStart(date)
    setDragEnd(date)
  }, [])

  const handleMouseEnter = useCallback((date: Date) => {
    if (isDragging.current && dragStart) {
      setDragEnd(date)
    }
  }, [dragStart])

  const handleMouseUp = useCallback(() => {
    if (isDragging.current && dragStart && dragEnd) {
      if (isSameDay(dragStart, dragEnd)) {
        onSelectDate(dragStart)
      } else {
        onSelectRange(dragStart, dragEnd)
      }
    }
    isDragging.current = false
    setDragStart(null)
    setDragEnd(null)
  }, [dragStart, dragEnd, onSelectDate, onSelectRange])

  const isInDragRange = useCallback((date: Date) => {
    if (!dragStart || !dragEnd) return false
    const start = dragStart < dragEnd ? dragStart : dragEnd
    const end = dragStart < dragEnd ? dragEnd : dragStart
    return date >= start && date <= end
  }, [dragStart, dragEnd])

  const isSelected = useCallback((date: Date) => {
    return selectedDates.some((d) => isSameDay(d, date))
  }, [selectedDates])

  return (
    <div
      className={`${styles.grid} ${styles[`grid-${view}`]}`}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <div className={styles.weekHeader}>
        {weekDays.map((day, i) => (
          <div key={i} className={styles.weekDay}>
            <span className={styles.weekDayFull}>{day.full}</span>
            <span className={styles.weekDayShort}>{day.short}</span>
          </div>
        ))}
      </div>

      <div className={styles.daysGrid}>
        {visibleDays.map((calDay) => {
          const diaData = getDiaData(calDay.date)
          const selected = isSelected(calDay.date)
          const inDragRange = isInDragRange(calDay.date)

          return (
            <DayCell
              key={format(calDay.date, 'yyyy-MM-dd')}
              calendarDay={calDay}
              diaData={diaData}
              hoverUsuarios={getHoverUsuarios?.(calDay.date) ?? []}
              capacityDisplay={getCapacityDisplay?.(calDay.date) ?? null}
              isSelected={selected}
              isInDragRange={inDragRange}
              isAdmin={isAdmin}
              loading={loading && !diaData}
              exibirIndicadorOcioso={exibirIndicadorOcioso}
              onMouseDown={(e) => handleMouseDown(calDay.date, e)}
              onMouseEnter={() => handleMouseEnter(calDay.date)}
              onClick={() => onDayClick(calDay.date, diaData)}
            />
          )
        })}
      </div>
    </div>
  )
}
