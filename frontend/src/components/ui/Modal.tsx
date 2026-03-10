// ============================================================
// Modal — Dialog overlay elegante
// ============================================================
import { useEffect, useRef, type ReactNode } from 'react'
import styles from './Modal.module.css'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  children: ReactNode
}

export default function Modal({ 
  open, 
  onClose, 
  title, 
  size = 'md',
  children 
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (open) {
      dialog.showModal()
    } else {
      dialog.close()
    }
  }, [open])

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [open, onClose])

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === dialogRef.current) {
      onClose()
    }
  }

  if (!open) return null

  return (
    <dialog
      ref={dialogRef}
      className={`${styles.dialog} ${styles[size]}`}
      onClick={handleBackdropClick}
    >
      <div className={styles.container}>
        {title && (
          <header className={styles.header}>
            <h2 className={styles.title}>{title}</h2>
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
      </div>
    </dialog>
  )
}

// Sub-componentes para composição
Modal.Footer = function ModalFooter({ children }: { children: ReactNode }) {
  return <footer className={styles.footer}>{children}</footer>
}
