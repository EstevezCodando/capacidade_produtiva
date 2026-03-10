// ============================================================
// Drawer — Painel lateral deslizante
// ============================================================
import { useEffect, useRef, type ReactNode } from 'react'
import styles from './Drawer.module.css'

interface DrawerProps {
  open: boolean
  onClose: () => void
  title?: string
  subtitle?: string
  position?: 'left' | 'right'
  width?: number | string
  children: ReactNode
}

export default function Drawer({ 
  open, 
  onClose, 
  title,
  subtitle,
  position = 'right',
  width = 420,
  children 
}: DrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [open, onClose])

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  return (
    <>
      {/* Backdrop */}
      <div 
        className={`${styles.backdrop} ${open ? styles.backdropVisible : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Drawer */}
      <aside
        ref={drawerRef}
        className={`${styles.drawer} ${styles[position]} ${open ? styles.open : ''}`}
        style={{ width: typeof width === 'number' ? `${width}px` : width }}
        role="dialog"
        aria-modal="true"
      >
        {(title || subtitle) && (
          <header className={styles.header}>
            <div className={styles.headerContent}>
              {title && <h2 className={styles.title}>{title}</h2>}
              {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
            </div>
            <button 
              className={styles.closeBtn} 
              onClick={onClose}
              aria-label="Fechar"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </header>
        )}
        <div className={styles.body}>
          {children}
        </div>
      </aside>
    </>
  )
}

// Sub-componentes
Drawer.Section = function DrawerSection({ 
  title, 
  children 
}: { 
  title?: string
  children: ReactNode 
}) {
  return (
    <section className={styles.section}>
      {title && <h3 className={styles.sectionTitle}>{title}</h3>}
      {children}
    </section>
  )
}

Drawer.Footer = function DrawerFooter({ children }: { children: ReactNode }) {
  return <footer className={styles.footer}>{children}</footer>
}
