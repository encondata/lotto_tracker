import { useEffect, useMemo, useRef } from 'react'
import gsap from 'gsap'
import { formatCents } from '../ui/Money'

export interface LineAreaPoint {
  /** X-axis label, e.g. '2026-03' or '2026-W12'. */
  label: string
  spent: number
  won: number
  net: number
}

interface LineAreaProps {
  data: LineAreaPoint[]
  /** Intrinsic drawing width for the viewBox (scales responsively). */
  width?: number
  height?: number
}

const PAD = { top: 18, right: 16, bottom: 30, left: 52 }

/** Compact currency for axis ticks, e.g. $1.2k / -$340. */
function tick(cents: number): string {
  const abs = Math.abs(cents)
  const sign = cents < 0 ? '-' : ''
  if (abs >= 100_000) return `${sign}$${(abs / 100_000).toFixed(abs >= 1_000_000 ? 0 : 1)}k`
  return `${sign}$${Math.round(abs / 100)}`
}

/** Trim a period label for display: '2026-03' -> "'26 03", '2026-W12' -> "'26 W12". */
function shortLabel(label: string): string {
  const m = label.match(/^(\d{4})-(W?\d+)$/)
  if (!m) return label
  return `'${m[1].slice(2)} ${m[2]}`
}

/**
 * Bespoke net/spent/won chart. Draws:
 *  - a net area (mint-tinted fill under a brass/loss net line)
 *  - a won line (mint) and spent line (muted)
 * Pure + responsive: takes data + dimensions, renders SVG at 100% width.
 */
export function LineArea({ data, width = 720, height = 260 }: LineAreaProps) {
  const wonRef = useRef<SVGPathElement>(null)
  const spentRef = useRef<SVGPathElement>(null)
  const netRef = useRef<SVGPathElement>(null)
  const areaRef = useRef<SVGPathElement>(null)

  const geom = useMemo(() => {
    const innerW = width - PAD.left - PAD.right
    const innerH = height - PAD.top - PAD.bottom

    const values: number[] = []
    for (const d of data) values.push(d.spent, d.won, d.net)
    let min = Math.min(0, ...values)
    let max = Math.max(0, ...values)
    if (min === max) {
      // Flat/empty — give the axis a nominal range so lines sit mid-frame.
      min = -100
      max = 100
    }
    // Small headroom so peaks don't touch the frame.
    const span = max - min || 1
    max += span * 0.08
    min -= span * 0.08

    const n = data.length
    const x = (i: number) =>
      PAD.left + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW)
    const y = (v: number) =>
      PAD.top + innerH - ((v - min) / (max - min)) * innerH
    const zeroY = y(0)

    const pathFor = (get: (p: LineAreaPoint) => number) => {
      if (n === 0) return ''
      if (n === 1) {
        // Draw a short flat segment so a single datapoint is visible.
        const cx = x(0)
        const cy = y(get(data[0]))
        return `M ${cx - innerW / 6} ${cy} L ${cx + innerW / 6} ${cy}`
      }
      return data
        .map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(get(p)).toFixed(1)}`)
        .join(' ')
    }

    const netLine = pathFor((p) => p.net)
    const areaPath =
      n === 0
        ? ''
        : n === 1
          ? (() => {
              const cx = x(0)
              const cy = y(data[0].net)
              const l = cx - innerW / 6
              const r = cx + innerW / 6
              return `M ${l} ${zeroY} L ${l} ${cy} L ${r} ${cy} L ${r} ${zeroY} Z`
            })()
          : `${netLine} L ${x(n - 1).toFixed(1)} ${zeroY.toFixed(1)} L ${x(0).toFixed(1)} ${zeroY.toFixed(1)} Z`

    // y-ticks: top, zero, bottom (dedup + sorted).
    const finalYTicks = Array.from(new Set([max, 0, min])).sort((a, b) => b - a)

    return {
      innerW,
      innerH,
      x,
      y,
      zeroY,
      wonPath: pathFor((p) => p.won),
      spentPath: pathFor((p) => p.spent),
      netLine,
      areaPath,
      netPositive: data.length ? data[data.length - 1].net >= 0 : true,
      yTicks: finalYTicks,
      points: data.map((p, i) => ({ x: x(i), y: y(p.net), p })),
      xLabels: data.map((p, i) => ({ x: x(i), label: shortLabel(p.label) })),
    }
  }, [data, width, height])

  // Stroke draw-on for the three lines.
  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const paths = [wonRef.current, spentRef.current, netRef.current].filter(
      Boolean,
    ) as SVGPathElement[]
    if (reduce) {
      paths.forEach((p) => {
        p.style.strokeDasharray = 'none'
        p.style.strokeDashoffset = '0'
      })
      if (areaRef.current) areaRef.current.style.opacity = '1'
      return
    }
    const tweens: gsap.core.Tween[] = []
    paths.forEach((p, idx) => {
      const len = p.getTotalLength()
      gsap.set(p, { strokeDasharray: len, strokeDashoffset: len })
      tweens.push(
        gsap.to(p, {
          strokeDashoffset: 0,
          duration: 1.1,
          ease: 'power2.out',
          delay: 0.08 * idx,
        }),
      )
    })
    if (areaRef.current) {
      gsap.fromTo(
        areaRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.9, ease: 'power1.out', delay: 0.25 },
      )
    }
    return () => {
      tweens.forEach((t) => t.kill())
    }
  }, [geom])

  const netColor = geom.netPositive ? 'var(--brass)' : 'var(--loss)'

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      role="img"
      aria-label="Spend and winnings over time"
      style={{ display: 'block', overflow: 'visible' }}
    >
      <defs>
        <linearGradient id="netfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={netColor} stopOpacity="0.24" />
          <stop offset="100%" stopColor={netColor} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* y gridlines + labels */}
      {geom.yTicks.map((v, i) => {
        const yy = geom.y(v)
        const isZero = v === 0
        return (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={width - PAD.right}
              y1={yy}
              y2={yy}
              stroke={isZero ? 'rgba(230,240,230,0.18)' : 'rgba(230,240,230,0.06)'}
              strokeWidth={isZero ? 1 : 1}
              strokeDasharray={isZero ? 'none' : '3 5'}
            />
            <text
              x={PAD.left - 8}
              y={yy + 3}
              textAnchor="end"
              fontFamily="var(--font-mono)"
              fontSize="10"
              fill="var(--muted)"
            >
              {tick(v)}
            </text>
          </g>
        )
      })}

      {/* net area */}
      {geom.areaPath && (
        <path ref={areaRef} d={geom.areaPath} fill="url(#netfill)" stroke="none" />
      )}

      {/* spent (muted) + won (mint) lines */}
      <path
        ref={spentRef}
        d={geom.spentPath}
        fill="none"
        stroke="var(--muted)"
        strokeWidth="1.6"
        strokeDasharray="4 4"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.85"
      />
      <path
        ref={wonRef}
        d={geom.wonPath}
        fill="none"
        stroke="var(--mint)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* net line on top */}
      <path
        ref={netRef}
        d={geom.netLine}
        fill="none"
        stroke={netColor}
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* net point markers */}
      {geom.points.map((pt, i) => (
        <circle
          key={i}
          cx={pt.x}
          cy={pt.y}
          r={3}
          fill="var(--ink)"
          stroke={netColor}
          strokeWidth="1.8"
        >
          <title>{`${pt.p.label} · net ${formatCents(pt.p.net, true)}`}</title>
        </circle>
      ))}

      {/* x labels */}
      {geom.xLabels.map((t, i) => {
        // Thin out labels when crowded.
        const step = Math.ceil(geom.xLabels.length / 7)
        if (geom.xLabels.length > 7 && i % step !== 0 && i !== geom.xLabels.length - 1)
          return null
        return (
          <text
            key={i}
            x={t.x}
            y={height - PAD.bottom + 18}
            textAnchor="middle"
            fontFamily="var(--font-mono)"
            fontSize="10"
            fill="var(--muted)"
          >
            {t.label}
          </text>
        )
      })}
    </svg>
  )
}
