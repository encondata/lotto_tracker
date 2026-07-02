import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchByGame,
  fetchOverTime,
  fetchPickBreakdown,
  fetchSummary,
  type OverTimeBucket,
  type PickSideBreakdown,
} from '../lib/api'
import { gameMeta } from '../lib/games'
import { StatCard } from '../components/ui/StatCard'
import { Panel } from '../components/ui/Panel'
import { GameChip } from '../components/ui/GameChip'
import { Money } from '../components/ui/Money'
import { LineArea, type LineAreaPoint } from '../components/charts/LineArea'
import { BarRow } from '../components/charts/BarRow'
import styles from './Analytics.module.css'

/** Resolve a css var like "var(--pb)" to a concrete color for inline SVG/canvas use. */
function resolveColor(cssVar: string): string {
  const m = cssVar.match(/var\((--[\w-]+)\)/)
  if (!m) return cssVar
  if (typeof window === 'undefined') return '#5fe3b0'
  const v = getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim()
  return v || cssVar
}

function Empty({ icon = '◇', children }: { icon?: string; children: React.ReactNode }) {
  return (
    <div className={styles.empty}>
      <span className={styles.emptyIcon} aria-hidden>
        {icon}
      </span>
      <span>{children}</span>
    </div>
  )
}

export default function Analytics() {
  const [bucket, setBucket] = useState<OverTimeBucket>('month')

  const summaryQ = useQuery({ queryKey: ['summary'], queryFn: fetchSummary })
  const byGameQ = useQuery({ queryKey: ['byGame'], queryFn: fetchByGame })
  const overTimeQ = useQuery({
    queryKey: ['overTime', bucket],
    queryFn: () => fetchOverTime(bucket),
  })
  const pickQ = useQuery({ queryKey: ['pickBreakdown'], queryFn: fetchPickBreakdown })

  const summary = summaryQ.data

  const linePoints: LineAreaPoint[] = useMemo(
    () =>
      (overTimeQ.data ?? []).map((d) => ({
        label: d.period,
        spent: d.spent_cents,
        won: d.won_cents,
        net: d.net_cents,
      })),
    [overTimeQ.data],
  )

  const games = useMemo(
    () => [...(byGameQ.data ?? [])].sort((a, b) => b.net_cents - a.net_cents),
    [byGameQ.data],
  )
  const gameMax = useMemo(
    () => Math.max(1, ...games.flatMap((g) => [g.won_cents, g.spent_cents])),
    [games],
  )

  return (
    <div className={styles.page}>
      <div>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          The numbers
        </div>
        <h1 className={styles.title}>Analytics</h1>
      </div>

      {/* HEADLINE STATS */}
      {summaryQ.isLoading && <p className={styles.loading}>Tallying the ledger…</p>}
      {summary && (
        <div className={styles.statGrid}>
          <StatCard
            label="Net"
            value={summary.net_cents}
            format="money"
            signed
            accent={summary.net_cents >= 0 ? 'brass' : 'loss'}
          />
          <StatCard label="Total won" value={summary.total_won_cents} format="money" accent="mint" />
          <StatCard
            label="Total spent"
            value={summary.total_spent_cents}
            format="money"
            accent="ivory"
          />
          <StatCard
            label="Win rate"
            value={summary.win_rate <= 1 ? summary.win_rate * 100 : summary.win_rate}
            format="percent"
            accent="mint"
          />
          <StatCard
            label="ROI"
            value={summary.roi_pct}
            format="percent"
            accent={summary.roi_pct >= 0 ? 'brass' : 'loss'}
          />
          <StatCard
            label="Biggest win"
            value={summary.biggest_win_cents}
            format="money"
            accent="brass"
          />
          <StatCard
            label="Pending"
            value={summary.pending_cents}
            format="money"
            accent="ivory"
            sub="in play"
          />
          <StatCard
            label="Lines played"
            value={summary.lines_played}
            format="int"
            accent="ivory"
            sub={`${summary.tickets_purchased} tickets`}
          />
        </div>
      )}

      {/* NET OVER TIME */}
      <Panel pad>
        <div className={styles.panelHead}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 4 }}>
              The arc
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.15rem' }}>
              Net over time
            </div>
          </div>
          <div className={styles.seg} role="tablist" aria-label="Time bucket">
            {(['month', 'week'] as OverTimeBucket[]).map((b) => (
              <button
                key={b}
                role="tab"
                aria-selected={bucket === b}
                className={`${styles.segBtn} ${bucket === b ? styles.segBtnActive : ''}`}
                onClick={() => setBucket(b)}
              >
                {b}
              </button>
            ))}
          </div>
        </div>

        {overTimeQ.isLoading && <p className={styles.loading}>Drawing the line…</p>}
        {overTimeQ.data && linePoints.length === 0 && (
          <Empty icon="↗">No plays recorded yet — your net line starts with your first ticket.</Empty>
        )}
        {linePoints.length > 0 && (
          <>
            <LineArea key={bucket} data={linePoints} />
            <div className={styles.legend}>
              <span className={styles.legendItem}>
                <span className={styles.swatch} style={{ background: 'var(--brass)' }} /> Net
              </span>
              <span className={styles.legendItem}>
                <span className={styles.swatch} style={{ background: 'var(--mint)' }} /> Won
              </span>
              <span className={styles.legendItem}>
                <span className={`${styles.swatch} ${styles.swatchDash}`} /> Spent
              </span>
            </div>
          </>
        )}
      </Panel>

      {/* BY GAME */}
      <Panel eyebrow="Where it went" title="By game">
        {byGameQ.isLoading && <p className={styles.loading}>Sorting the games…</p>}
        {byGameQ.data && games.length === 0 && (
          <Empty icon="◈">No game activity yet.</Empty>
        )}
        {games.length > 0 && (
          <div className={styles.gameRows}>
            {games.map((g) => {
              const color = resolveColor(gameMeta(g.game_key).color)
              return (
                <div key={g.game_key} className={styles.gameRow}>
                  <GameChip gameKey={g.game_key} size="sm" />
                  <div className={styles.gameBar}>
                    <BarRow won={g.won_cents} spent={g.spent_cents} max={gameMax} color={color} />
                  </div>
                  <div className={styles.gameNet}>
                    <Money cents={g.net_cents} signed tone />
                    <div className={styles.gameNetSub}>
                      won <Money cents={g.won_cents} /> · spent <Money cents={g.spent_cents} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Panel>

      {/* QUICK VS SELF PICK */}
      <Panel eyebrow="Your style" title="Quick pick vs self pick">
        {pickQ.isLoading && <p className={styles.loading}>Comparing styles…</p>}
        {pickQ.data && <PickCompare quick={pickQ.data.quick_pick} self={pickQ.data.self_pick} />}
      </Panel>
    </div>
  )
}

function PickCompare({
  quick,
  self,
}: {
  quick: PickSideBreakdown
  self: PickSideBreakdown
}) {
  const qRate = quick.win_rate <= 1 ? quick.win_rate * 100 : quick.win_rate
  const sRate = self.win_rate <= 1 ? self.win_rate * 100 : self.win_rate
  const noData = quick.lines === 0 && self.lines === 0
  if (noData) {
    return <Empty icon="⚄">No lines played yet — this fills in as you add tickets.</Empty>
  }

  const cards = [
    { key: 'quick', label: 'Quick pick', side: quick, rate: qRate, color: 'var(--mint)' },
    { key: 'self', label: 'Self pick', side: self, rate: sRate, color: 'var(--brass)' },
  ]
  const best = qRate === sRate ? null : qRate > sRate ? 'quick' : 'self'
  // Scale meters against the higher of the two so the winner reads full-ish.
  const maxRate = Math.max(qRate, sRate, 1)

  return (
    <div className={styles.pickGrid}>
      {cards.map((c) => (
        <div
          key={c.key}
          className={`${styles.pickCard} ${best === c.key ? styles.pickCardTop : ''}`}
        >
          <div className={styles.pickHead}>
            <span className={styles.pickLabel}>{c.label}</span>
            {best === c.key && (
              <span
                className="eyebrow"
                style={{ color: 'var(--mint)', letterSpacing: '0.12em' }}
              >
                ★ Better
              </span>
            )}
          </div>
          <div className={styles.pickRate} style={{ color: c.color }}>
            {c.rate.toFixed(1)}%
          </div>
          <div className={styles.pickMeter}>
            <div
              className={styles.pickMeterFill}
              style={{
                width: `${Math.min(100, (c.rate / maxRate) * 100)}%`,
                background: c.color,
                boxShadow: `0 0 12px -3px ${c.color}`,
              }}
            />
          </div>
          <div className={styles.pickMeta}>
            {c.side.wins.toLocaleString('en-US')} wins · {c.side.lines.toLocaleString('en-US')} lines
          </div>
        </div>
      ))}
    </div>
  )
}
