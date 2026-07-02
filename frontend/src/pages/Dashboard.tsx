import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import gsap from 'gsap'
import { fetchDraws, fetchSummary, fetchTickets, type Draw } from '../lib/api'
import { gameMeta } from '../lib/games'
import { GameChip } from '../components/ui/GameChip'
import { StatCard } from '../components/ui/StatCard'
import { Panel } from '../components/ui/Panel'
import { BallRow } from '../components/ui/Ball'
import { Money } from '../components/ui/Money'
import { Pill } from '../components/ui/Pill'
import styles from './Dashboard.module.css'

const DrawStudio = lazy(() => import('../three/DrawStudio'))

/** Resolve a css var like "var(--pb)" to a concrete hex for the WebGL scene. */
function resolveColor(cssVar: string): string {
  const m = cssVar.match(/var\((--[\w-]+)\)/)
  if (!m) return cssVar
  if (typeof window === 'undefined') return '#5fe3b0'
  const v = getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim()
  return v || '#5fe3b0'
}

// Preferred order when picking a default game to feature.
const GAME_PRIORITY = ['powerball', 'mega_millions', 'lotto_texas', 'texas_two_step', 'daily_4']

export default function Dashboard() {
  const summaryQ = useQuery({ queryKey: ['summary'], queryFn: fetchSummary })
  const drawsQ = useQuery({ queryKey: ['draws', 10], queryFn: () => fetchDraws(10) })
  const ticketsQ = useQuery({ queryKey: ['tickets'], queryFn: fetchTickets })

  const draws = drawsQ.data ?? []

  // Latest draw per game.
  const latestByGame = useMemo(() => {
    const map = new Map<string, Draw>()
    for (const d of draws) {
      const cur = map.get(d.game_key)
      if (!cur || d.draw_date > cur.draw_date) map.set(d.game_key, d)
    }
    return map
  }, [draws])

  const gameKeys = useMemo(() => {
    const keys = Array.from(latestByGame.keys())
    keys.sort((a, b) => {
      const ia = GAME_PRIORITY.indexOf(a)
      const ib = GAME_PRIORITY.indexOf(b)
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
    })
    return keys
  }, [latestByGame])

  const [selected, setSelected] = useState<string | null>(null)
  useEffect(() => {
    if (!selected && gameKeys.length) {
      const preferred = gameKeys.find((k) => k === 'powerball') ?? gameKeys[0]
      setSelected(preferred)
    }
  }, [gameKeys, selected])

  const featured = selected ? latestByGame.get(selected) : undefined
  const heroNumbers = featured
    ? [...featured.winning_main, ...(featured.winning_special != null ? [featured.winning_special] : [])]
    : []
  const accent = featured ? resolveColor(gameMeta(featured.game_key).color) : '#5fe3b0'

  const summary = summaryQ.data
  const hasUnclaimed = (summary?.total_won_cents ?? 0) > 0

  // Stagger-reveal on load.
  const gridRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!summary || !gridRef.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const cards = gridRef.current.querySelectorAll('[data-reveal]')
    gsap.fromTo(
      cards,
      { y: 18, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.5, ease: 'power2.out', stagger: 0.07 },
    )
  }, [summary])

  const recentTickets = (ticketsQ.data ?? []).slice(0, 4)

  return (
    <div className={styles.page} ref={gridRef}>
      <div className={styles.head}>
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            The draw room
          </div>
          <h1 className={styles.title}>Dashboard</h1>
        </div>
      </div>

      {/* HERO */}
      <div className={styles.hero} data-reveal>
        <div className={styles.heroChips}>
          {gameKeys.map((k) => (
            <GameChip
              key={k}
              gameKey={k}
              size="sm"
              active={k === selected}
              onClick={() => setSelected(k)}
            />
          ))}
        </div>

        {drawsQ.isLoading ? (
          <div className={styles.heroFallback}>Warming up the studio…</div>
        ) : (
          <Suspense fallback={<div className={styles.heroFallback}>Loading scene…</div>}>
            <DrawStudio numbers={heroNumbers} accentColor={accent} celebrate={hasUnclaimed} height={340} />
          </Suspense>
        )}

        {featured && (
          <div className={styles.heroCaption}>
            <Pill tone="muted">
              {gameMeta(featured.game_key).name} · {featured.draw_date}
            </Pill>
          </div>
        )}
      </div>

      {/* UNCLAIMED BANNER */}
      {hasUnclaimed && (
        <div className={styles.banner} data-reveal>
          <span style={{ fontSize: '1.3rem' }} aria-hidden>
            ★
          </span>
          <span className={styles.bannerText}>You have unclaimed wins —</span>
          <Money cents={summary?.total_won_cents ?? 0} tone />
        </div>
      )}

      {/* STAT CARDS */}
      {summary && (
        <div className={styles.statGrid}>
          <div data-reveal>
            <StatCard
              label="Net"
              value={summary.net_cents}
              format="money"
              signed
              accent={summary.net_cents >= 0 ? 'brass' : 'loss'}
            />
          </div>
          <div data-reveal>
            <StatCard label="Total won" value={summary.total_won_cents} format="money" accent="mint" />
          </div>
          <div data-reveal>
            <StatCard label="Total spent" value={summary.total_spent_cents} format="money" accent="ivory" />
          </div>
          <div data-reveal>
            <StatCard
              label="Win rate"
              value={summary.win_rate <= 1 ? summary.win_rate * 100 : summary.win_rate}
              format="percent"
              accent="mint"
            />
          </div>
          <div data-reveal>
            <StatCard
              label="Tickets"
              value={summary.tickets_purchased}
              format="int"
              accent="ivory"
              sub={`${summary.lines_played} lines`}
            />
          </div>
        </div>
      )}

      {/* RECENT TICKETS */}
      <div data-reveal>
        <Panel eyebrow="Latest plays" title="Recent tickets" pad={false} style={{ padding: 20 }}>
          {ticketsQ.isLoading && <p style={{ color: 'var(--muted)', margin: 0 }}>Loading…</p>}
          {ticketsQ.data && recentTickets.length === 0 && (
            <p style={{ color: 'var(--muted)', margin: 0 }}>No tickets yet.</p>
          )}
          {recentTickets.length > 0 && (
            <div className={styles.strip}>
              {recentTickets.map((t) => {
                const meta = gameMeta(t.game_key)
                const line = t.lines[0]
                const won = t.total_won_cents > 0
                return (
                  <Link key={t.id} to={`/tickets/${t.id}`} className={styles.ticketCard}>
                    <div className={styles.ticketMeta}>
                      <GameChip gameKey={t.game_key} size="sm" />
                      <span>{t.purchase_date}</span>
                    </div>
                    {line && (
                      <BallRow
                        main={line.main_numbers}
                        special={line.special_number}
                        size="sm"
                        pad={meta.isDaily4 ? 1 : 0}
                      />
                    )}
                    <div style={{ marginTop: 'auto' }}>
                      {won ? (
                        <Pill tone="brass">
                          Won <Money cents={t.total_won_cents} />
                        </Pill>
                      ) : (
                        <span style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
                          Spent <Money cents={t.total_cost_cents} />
                        </span>
                      )}
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
        </Panel>
      </div>

      {/* LATEST NUMBERS */}
      <div data-reveal>
        <Panel eyebrow="Results" title="Latest numbers">
          {drawsQ.isLoading && <p style={{ color: 'var(--muted)', margin: 0 }}>Loading draws…</p>}
          {gameKeys.length === 0 && !drawsQ.isLoading && (
            <p style={{ color: 'var(--muted)', margin: 0 }}>No draws available.</p>
          )}
          {gameKeys.map((k) => {
            const d = latestByGame.get(k)!
            const meta = gameMeta(k)
            return (
              <div key={k} className={styles.drawRow}>
                <GameChip gameKey={k} size="sm" />
                <BallRow
                  main={d.winning_main}
                  special={d.winning_special}
                  size="sm"
                  pad={meta.isDaily4 ? 1 : 0}
                />
                <span className={styles.drawDate}>{d.draw_date}</span>
              </div>
            )
          })}
        </Panel>
      </div>
    </div>
  )
}
