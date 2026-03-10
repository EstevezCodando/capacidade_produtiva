// ============================================================
// UI Components — Botões, Badges, Cards e utilitários
// ============================================================
import type { ReactNode, ButtonHTMLAttributes } from 'react'
import styles from './Common.module.css'

// ══════════════════════════════════════════════════════════════
// Button
// ══════════════════════════════════════════════════════════════

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: ReactNode
}

export function Button({ 
  variant = 'secondary', 
  size = 'md',
  loading,
  icon,
  children,
  disabled,
  className = '',
  ...props 
}: ButtonProps) {
  return (
    <button
      className={`${styles.btn} ${styles[`btn-${variant}`]} ${styles[`btn-${size}`]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className={styles.spinner} />
      ) : icon ? (
        <span className={styles.btnIcon}>{icon}</span>
      ) : null}
      {children}
    </button>
  )
}

// ══════════════════════════════════════════════════════════════
// Badge
// ══════════════════════════════════════════════════════════════

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
  size?: 'sm' | 'md'
  children: ReactNode
}

export function Badge({ variant = 'default', size = 'sm', children }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[`badge-${variant}`]} ${styles[`badge-${size}`]}`}>
      {children}
    </span>
  )
}

// ══════════════════════════════════════════════════════════════
// Card
// ══════════════════════════════════════════════════════════════

interface CardProps {
  title?: string
  subtitle?: string
  action?: ReactNode
  padding?: 'none' | 'sm' | 'md' | 'lg'
  className?: string
  children: ReactNode
}

export function Card({ 
  title, 
  subtitle, 
  action, 
  padding = 'md',
  className = '',
  children 
}: CardProps) {
  return (
    <div className={`${styles.card} ${className}`}>
      {(title || action) && (
        <div className={styles.cardHeader}>
          <div>
            {title && <h3 className={styles.cardTitle}>{title}</h3>}
            {subtitle && <p className={styles.cardSubtitle}>{subtitle}</p>}
          </div>
          {action && <div className={styles.cardAction}>{action}</div>}
        </div>
      )}
      <div className={`${styles.cardBody} ${styles[`padding-${padding}`]}`}>
        {children}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// Skeleton
// ══════════════════════════════════════════════════════════════

interface SkeletonProps {
  width?: string | number
  height?: string | number
  variant?: 'text' | 'rect' | 'circle'
  className?: string
}

export function Skeleton({ 
  width = '100%', 
  height = 16, 
  variant = 'rect',
  className = ''
}: SkeletonProps) {
  return (
    <div 
      className={`${styles.skeleton} ${styles[`skeleton-${variant}`]} ${className}`}
      style={{ 
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height
      }}
    />
  )
}

// ══════════════════════════════════════════════════════════════
// EmptyState
// ══════════════════════════════════════════════════════════════

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className={styles.empty}>
      {icon && <div className={styles.emptyIcon}>{icon}</div>}
      <h4 className={styles.emptyTitle}>{title}</h4>
      {description && <p className={styles.emptyDesc}>{description}</p>}
      {action && <div className={styles.emptyAction}>{action}</div>}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// StatCard — card numérico com label
// ══════════════════════════════════════════════════════════════

interface StatCardProps {
  label: string
  value: string | number
  suffix?: string
  variant?: 'default' | 'accent' | 'success' | 'warning' | 'error'
  trend?: { value: number; label?: string }
  size?: 'sm' | 'md' | 'lg'
}

export function StatCard({ 
  label, 
  value, 
  suffix, 
  variant = 'default',
  trend,
  size = 'md'
}: StatCardProps) {
  const trendPositive = trend && trend.value >= 0

  return (
    <div className={`${styles.stat} ${styles[`stat-${size}`]}`}>
      <span className={styles.statLabel}>{label}</span>
      <div className={styles.statValueRow}>
        <span className={`${styles.statValue} ${styles[`stat-${variant}`]}`}>
          {value}
          {suffix && <span className={styles.statSuffix}>{suffix}</span>}
        </span>
        {trend && (
          <span className={`${styles.statTrend} ${trendPositive ? styles.trendUp : styles.trendDown}`}>
            {trendPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
            {trend.label && <span className={styles.trendLabel}>{trend.label}</span>}
          </span>
        )}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// ProgressBar — barra de progresso
// ══════════════════════════════════════════════════════════════

interface ProgressBarProps {
  value: number
  max?: number
  variant?: 'default' | 'success' | 'warning' | 'error'
  showLabel?: boolean
  size?: 'sm' | 'md'
  className?: string
}

export function ProgressBar({ 
  value, 
  max = 100, 
  variant = 'default',
  showLabel = false,
  size = 'md',
  className = ''
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))
  
  return (
    <div className={`${styles.progressWrap} ${className}`}>
      <div className={`${styles.progressTrack} ${styles[`progress-${size}`]}`}>
        <div 
          className={`${styles.progressFill} ${styles[`progress-${variant}`]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className={styles.progressLabel}>{Math.round(percentage)}%</span>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// CapacityBar — barra dual (normal + extra)
// ══════════════════════════════════════════════════════════════

interface CapacityBarProps {
  normalValue: number
  normalMax: number
  extraValue?: number
  extraMax?: number
  showLabels?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function CapacityBar({ 
  normalValue, 
  normalMax, 
  extraValue = 0,
  extraMax = 0,
  showLabels = true,
  size = 'md'
}: CapacityBarProps) {
  const totalMax = normalMax + extraMax
  const normalPct = totalMax > 0 ? (normalValue / totalMax) * 100 : 0
  const extraPct = totalMax > 0 ? (extraValue / totalMax) * 100 : 0
  const normalMaxPct = totalMax > 0 ? (normalMax / totalMax) * 100 : 100

  return (
    <div className={styles.capacityWrap}>
      <div className={`${styles.capacityTrack} ${styles[`capacity-${size}`]}`}>
        {/* Zona normal */}
        <div 
          className={styles.capacityNormalZone}
          style={{ width: `${normalMaxPct}%` }}
        />
        {/* Fill normal */}
        <div 
          className={styles.capacityNormalFill}
          style={{ width: `${Math.min(normalPct, normalMaxPct)}%` }}
        />
        {/* Fill extra */}
        {extraValue > 0 && (
          <div 
            className={styles.capacityExtraFill}
            style={{ 
              left: `${normalMaxPct}%`,
              width: `${extraPct}%` 
            }}
          />
        )}
        {/* Marcador de transição */}
        <div 
          className={styles.capacityMarker}
          style={{ left: `${normalMaxPct}%` }}
        />
      </div>
      {showLabels && (
        <div className={styles.capacityLabels}>
          <span className={styles.capacityLabelNormal}>
            {normalValue}/{normalMax}min
          </span>
          {extraMax > 0 && (
            <span className={styles.capacityLabelExtra}>
              +{extraValue}/{extraMax}min
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// Select — dropdown estilizado
// ══════════════════════════════════════════════════════════════

interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
}

interface SelectProps {
  value: string | number
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  size?: 'sm' | 'md'
  className?: string
}

export function Select({
  value,
  onChange,
  options,
  placeholder,
  disabled,
  size = 'md',
  className = ''
}: SelectProps) {
  return (
    <select
      className={`${styles.select} ${styles[`select-${size}`]} ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
    >
      {placeholder && (
        <option value="" disabled>{placeholder}</option>
      )}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} disabled={opt.disabled}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}

// ══════════════════════════════════════════════════════════════
// Input
// ══════════════════════════════════════════════════════════════

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export function Input({
  label,
  error,
  hint,
  className = '',
  ...props
}: InputProps) {
  return (
    <div className={styles.inputWrap}>
      {label && <label className={styles.inputLabel}>{label}</label>}
      <input
        className={`${styles.input} ${error ? styles.inputError : ''} ${className}`}
        {...props}
      />
      {error && <span className={styles.inputErrorMsg}>{error}</span>}
      {hint && !error && <span className={styles.inputHint}>{hint}</span>}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// Textarea
// ══════════════════════════════════════════════════════════════

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export function Textarea({
  label,
  error,
  className = '',
  ...props
}: TextareaProps) {
  return (
    <div className={styles.inputWrap}>
      {label && <label className={styles.inputLabel}>{label}</label>}
      <textarea
        className={`${styles.textarea} ${error ? styles.inputError : ''} ${className}`}
        {...props}
      />
      {error && <span className={styles.inputErrorMsg}>{error}</span>}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// Tabs
// ══════════════════════════════════════════════════════════════

interface Tab {
  id: string
  label: string
  icon?: ReactNode
  badge?: string | number
}

interface TabsProps {
  tabs: Tab[]
  activeId: string
  onChange: (id: string) => void
  variant?: 'default' | 'pills'
}

export function Tabs({ tabs, activeId, onChange, variant = 'default' }: TabsProps) {
  return (
    <div className={`${styles.tabs} ${styles[`tabs-${variant}`]}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`${styles.tabItem} ${activeId === tab.id ? styles.tabActive : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.icon && <span className={styles.tabIcon}>{tab.icon}</span>}
          {tab.label}
          {tab.badge !== undefined && (
            <span className={styles.tabBadge}>{tab.badge}</span>
          )}
        </button>
      ))}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// Tooltip
// ══════════════════════════════════════════════════════════════

interface TooltipProps {
  content: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  children: ReactNode
}

export function Tooltip({ content, position = 'top', children }: TooltipProps) {
  return (
    <div className={styles.tooltipWrap}>
      {children}
      <span className={`${styles.tooltip} ${styles[`tooltip-${position}`]}`}>
        {content}
      </span>
    </div>
  )
}
