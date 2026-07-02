import styles from './Ball.module.css'

export type BallVariant = 'main' | 'special' | 'win'
export type BallSize = 'sm' | 'md' | 'lg'

interface BallProps {
  number: number
  variant?: BallVariant
  size?: BallSize
  title?: string
  /** For Daily-4 style single digits, pad to keep width consistent. */
  pad?: number
}

export function Ball({ number, variant = 'main', size = 'md', title, pad = 0 }: BallProps) {
  const label = pad > 0 ? String(number).padStart(pad, '0') : String(number)
  const variantClass =
    variant === 'special' ? styles.special : variant === 'win' ? styles.win : ''
  return (
    <span
      className={`${styles.ball} ${styles[size]} ${variantClass}`}
      title={title}
      aria-label={title ?? `Number ${label}`}
    >
      <span className={styles.num}>{label}</span>
    </span>
  )
}

interface BallRowProps {
  main: number[]
  special?: number | null
  size?: BallSize
  pad?: number
}

/** Convenience: a row of main balls plus an optional special ball. */
export function BallRow({ main, special, size = 'md', pad = 0 }: BallRowProps) {
  return (
    <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
      {main.map((n, i) => (
        <Ball key={`m-${i}`} number={n} variant="main" size={size} pad={pad} />
      ))}
      {special != null && (
        <Ball number={special} variant="special" size={size} pad={pad} />
      )}
    </span>
  )
}
