// ============================================================
// CalendarHeader — Barra de navegação temporal elegante
// ============================================================
import type { CalendarView } from '@/types/agenda'
import styles from './Calendar.module.css'

interface CalendarHeaderProps {
  periodLabel: string
  view: CalendarView
  onViewChange: (view: CalendarView) => void
  onPrev: () => void
  onNext: () => void
  onToday: () => void
  loading?: boolean
}

export default function CalendarHeader({
  periodLabel,
  onPrev,
  onNext,
  onToday,
  loading,
}: Omit<CalendarHeaderProps, 'view' | 'onViewChange'>) {
  return (
    <header className={styles.header}>
      {/* Navegação temporal */}
      <div className={styles.navGroup}>
        <button
          className={styles.navBtn}
          onClick={onPrev}
          aria-label="Período anterior"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>

        <button
          className={styles.todayBtn}
          onClick={onToday}
        >
          Hoje
        </button>

        <button
          className={styles.navBtn}
          onClick={onNext}
          aria-label="Próximo período"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      </div>

      {/* Label do período */}
      <h2 className={styles.periodLabel}>
        {periodLabel}
        {loading && <span className={styles.loadingDot} />}
      </h2>
    </header>
  )
}
