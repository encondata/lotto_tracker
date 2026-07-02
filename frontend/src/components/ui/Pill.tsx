import type { ReactNode } from 'react'

interface PillProps {
  children: ReactNode
  tone?: 'default' | 'mint' | 'brass' | 'loss' | 'muted'
  active?: boolean
  onClick?: () => void
  as?: 'span' | 'button'
  title?: string
}

const TONES: Record<string, { fg: string; bg: string; border: string }> = {
  default: { fg: 'var(--ivory)', bg: 'var(--surface-2)', border: 'var(--line)' },
  mint: { fg: '#05231a', bg: 'var(--mint)', border: 'transparent' },
  brass: { fg: '#241703', bg: 'var(--brass)', border: 'transparent' },
  loss: { fg: '#2a0f08', bg: 'var(--loss)', border: 'transparent' },
  muted: { fg: 'var(--muted)', bg: 'transparent', border: 'var(--line)' },
}

export function Pill({
  children,
  tone = 'default',
  active = false,
  onClick,
  as,
  title,
}: PillProps) {
  const t = TONES[tone]
  const Comp = as ?? (onClick ? 'button' : 'span')
  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '5px 12px',
    borderRadius: 'var(--r-pill)',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.72rem',
    fontWeight: 700,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    color: active ? '#05231a' : t.fg,
    background: active ? 'var(--mint)' : t.bg,
    border: `1px solid ${active ? 'transparent' : t.border}`,
    cursor: onClick ? 'pointer' : 'default',
    transition: 'background var(--dur) var(--ease), color var(--dur) var(--ease)',
    lineHeight: 1.4,
  }
  return (
    <Comp style={style} onClick={onClick} title={title}>
      {children}
    </Comp>
  )
}
