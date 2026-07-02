import { useEffect, useRef } from 'react'
import gsap from 'gsap'

interface BarRowProps {
  /** Won amount (cents) — drawn in the game color. */
  won: number
  /** Spent amount (cents) — drawn as a muted underlay. */
  spent: number
  /** Max across all rows, for a shared scale. */
  max: number
  /** Concrete color for the won bar (already resolved css var string is fine). */
  color: string
  height?: number
}

/**
 * One horizontal comparison bar: a muted "spent" underlay with the "won"
 * bar drawn in the game color on top. Pure + responsive (percentage widths),
 * animates its width on mount.
 */
export function BarRow({ won, spent, max, color, height = 26 }: BarRowProps) {
  const wonRef = useRef<HTMLDivElement>(null)
  const spentRef = useRef<HTMLDivElement>(null)

  const denom = max > 0 ? max : 1
  const wonPct = Math.max(0, Math.min(100, (won / denom) * 100))
  const spentPct = Math.max(0, Math.min(100, (spent / denom) * 100))

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const targets = [
      { el: spentRef.current, pct: spentPct, delay: 0 },
      { el: wonRef.current, pct: wonPct, delay: 0.1 },
    ]
    if (reduce) {
      targets.forEach((t) => {
        if (t.el) t.el.style.width = `${t.pct}%`
      })
      return
    }
    const tweens = targets.map(({ el, pct, delay }) =>
      el
        ? gsap.fromTo(
            el,
            { width: '0%' },
            { width: `${pct}%`, duration: 0.85, ease: 'power2.out', delay },
          )
        : null,
    )
    return () => {
      tweens.forEach((t) => t?.kill())
    }
  }, [wonPct, spentPct])

  return (
    <div
      style={{
        position: 'relative',
        height,
        borderRadius: 8,
        background: 'var(--ink-2)',
        border: '1px solid var(--line)',
        overflow: 'hidden',
      }}
    >
      {/* spent underlay */}
      <div
        ref={spentRef}
        style={{
          position: 'absolute',
          inset: '0 auto 0 0',
          width: 0,
          background:
            'repeating-linear-gradient(135deg, rgba(159,179,166,0.16) 0 6px, rgba(159,179,166,0.06) 6px 12px)',
        }}
        aria-hidden
      />
      {/* won bar */}
      <div
        ref={wonRef}
        style={{
          position: 'absolute',
          inset: '0 auto 0 0',
          width: 0,
          background: `linear-gradient(90deg, ${color}, ${color})`,
          boxShadow: `0 0 14px -4px ${color}`,
          borderRadius: '0 6px 6px 0',
          opacity: 0.92,
        }}
        aria-hidden
      />
    </div>
  )
}
