import { gameMeta } from '../../lib/games'

interface GameChipProps {
  gameKey: string
  size?: 'sm' | 'md'
  onClick?: () => void
  active?: boolean
}

export function GameChip({ gameKey, size = 'md', onClick, active = false }: GameChipProps) {
  const meta = gameMeta(gameKey)
  const isSm = size === 'sm'
  const Comp = onClick ? 'button' : 'span'
  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: isSm ? '4px 10px' : '6px 14px',
    borderRadius: 'var(--r-pill)',
    background: active ? 'var(--surface-2)' : 'var(--surface)',
    border: `1px solid ${active ? 'rgba(95,227,176,0.4)' : 'var(--line)'}`,
    color: 'var(--ivory)',
    fontFamily: 'var(--font-body)',
    fontWeight: 600,
    fontSize: isSm ? '0.78rem' : '0.9rem',
    cursor: onClick ? 'pointer' : 'default',
    transition: 'border-color var(--dur) var(--ease), background var(--dur) var(--ease)',
    whiteSpace: 'nowrap',
  }
  return (
    <Comp style={style} onClick={onClick} title={meta.name}>
      <span
        aria-hidden
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: meta.color,
          boxShadow: `0 0 8px -1px ${meta.color}`,
          flex: '0 0 auto',
        }}
      />
      {meta.name}
    </Comp>
  )
}
