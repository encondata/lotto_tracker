import type { CSSProperties, ReactNode } from 'react'
import styles from './Panel.module.css'

interface PanelProps {
  children: ReactNode
  title?: ReactNode
  eyebrow?: string
  action?: ReactNode
  pad?: boolean
  className?: string
  style?: CSSProperties
}

export function Panel({
  children,
  title,
  eyebrow,
  action,
  pad = true,
  className = '',
  style,
}: PanelProps) {
  return (
    <section className={`${styles.panel} ${pad ? styles.pad : ''} ${className}`} style={style}>
      {(title || action || eyebrow) && (
        <header className={styles.header}>
          <div>
            {eyebrow && <div className="eyebrow" style={{ marginBottom: 4 }}>{eyebrow}</div>}
            {title && <div className={styles.title}>{title}</div>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

/** Alias — a generic content card. */
export const Card = Panel
