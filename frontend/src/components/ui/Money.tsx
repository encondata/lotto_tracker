interface MoneyProps {
  cents: number
  /** Prefix with +/- sign (useful for net). */
  signed?: boolean
  className?: string
  /** Color positive brass / negative loss. */
  tone?: boolean
}

export function formatCents(cents: number, signed = false): string {
  const dollars = Math.abs(cents) / 100
  const body = dollars.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  const neg = cents < 0
  const sign = neg ? '-' : signed ? '+' : ''
  return `${sign}$${body}`
}

export function Money({ cents, signed = false, className, tone = false }: MoneyProps) {
  const style: React.CSSProperties = { fontFamily: 'var(--font-mono)' }
  if (tone) {
    style.color = cents < 0 ? 'var(--loss)' : cents > 0 ? 'var(--brass)' : 'var(--muted)'
  }
  return (
    <span className={className} style={style}>
      {formatCents(cents, signed)}
    </span>
  )
}
