import { useCountUp } from '../../lib/useCountUp'
import { formatCents } from './Money'
import { Ball } from './Ball'
import styles from './StatCard.module.css'

type Accent = 'brass' | 'mint' | 'loss' | 'ivory'

const accentClass: Record<Accent, string> = {
  brass: styles.accentBrass,
  mint: styles.accentMint,
  loss: styles.accentLoss,
  ivory: styles.accentIvory,
}

const accentColor: Record<Accent, string> = {
  brass: 'var(--brass)',
  mint: 'var(--mint)',
  loss: 'var(--loss)',
  ivory: 'var(--ivory)',
}

interface StatCardProps {
  label: string
  /** Raw numeric value to count up to. */
  value: number
  /** How to render the counted value. */
  format?: 'money' | 'percent' | 'int'
  /** For money: show +/- sign. */
  signed?: boolean
  accent?: Accent
  sub?: string
  animate?: boolean
}

function render(value: number, format: StatCardProps['format'], signed?: boolean): string {
  switch (format) {
    case 'money':
      return formatCents(Math.round(value), signed)
    case 'percent':
      return `${value.toFixed(1)}%`
    case 'int':
    default:
      return Math.round(value).toLocaleString('en-US')
  }
}

export function StatCard({
  label,
  value,
  format = 'int',
  signed = false,
  accent = 'ivory',
  sub,
  animate = true,
}: StatCardProps) {
  const counted = useCountUp(animate ? value : value)
  const shown = animate ? counted : value
  return (
    <div className={styles.stat}>
      <span className={styles.rail} style={{ background: accentColor[accent] }} />
      <div className={styles.label}>{label}</div>
      <div className={`${styles.value} ${accentClass[accent]}`}>
        {render(shown, format, signed)}
      </div>
      {sub && <div className={styles.sub}>{sub}</div>}
    </div>
  )
}

interface StatBallProps {
  label: string
  number: number
  sub?: string
  variant?: 'main' | 'special' | 'win'
}

/** A stat presented with the recurring lottery-ball motif. */
export function StatBall({ label, number, sub, variant = 'main' }: StatBallProps) {
  return (
    <div className={styles.stat}>
      <div className={styles.ballWrap}>
        <Ball number={number} size="lg" variant={variant} />
        <div>
          <div className={styles.label}>{label}</div>
          {sub && <div className={styles.sub}>{sub}</div>}
        </div>
      </div>
    </div>
  )
}
