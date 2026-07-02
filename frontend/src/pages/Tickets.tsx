import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import gsap from 'gsap'
import { fetchTickets, type Ticket } from '../lib/api'
import { gameMeta, GAMES } from '../lib/games'
import { GameChip } from '../components/ui/GameChip'
import { BallRow } from '../components/ui/Ball'
import { Money } from '../components/ui/Money'
import { Pill } from '../components/ui/Pill'
import { Button } from '../components/ui/Button'
import styles from './Tickets.module.css'

type StatusFilter = 'all' | 'won' | 'pending' | 'no_win'

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'won', label: 'Won' },
  { key: 'pending', label: 'Pending' },
  { key: 'no_win', label: 'No win' },
]

/** Derive a settlement status for a ticket from its results. */
function ticketStatus(t: Ticket): 'won' | 'pending' | 'no_win' {
  if (t.total_won_cents > 0) return 'won'
  if (t.results.length === 0 || t.results.some((r) => r.status === 'pending')) return 'pending'
  return 'no_win'
}

function ResultBadge({ t }: { t: Ticket }) {
  const s = ticketStatus(t)
  if (s === 'won') {
    return (
      <Pill tone="brass">
        Won&nbsp;<Money cents={t.total_won_cents} />
      </Pill>
    )
  }
  if (s === 'pending') return <Pill tone="muted">Pending</Pill>
  return <Pill tone="muted">No win</Pill>
}

export default function Tickets() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({ queryKey: ['tickets'], queryFn: fetchTickets })

  const [gameFilter, setGameFilter] = useState<string | null>(null)
  const [status, setStatus] = useState<StatusFilter>('all')

  const tickets = data ?? []

  // Games actually present in the ledger (so we don't show empty filters).
  const presentGames = useMemo(() => {
    const seen = new Set(tickets.map((t) => t.game_key))
    return Object.keys(GAMES).filter((k) => seen.has(k))
  }, [tickets])

  const filtered = useMemo(() => {
    return tickets.filter((t) => {
      if (gameFilter && t.game_key !== gameFilter) return false
      if (status !== 'all' && ticketStatus(t) !== status) return false
      return true
    })
  }, [tickets, gameFilter, status])

  // Stagger reveal on filter/data change.
  const listRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!listRef.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const cards = listRef.current.querySelectorAll('[data-reveal]')
    if (!cards.length) return
    gsap.fromTo(
      cards,
      { y: 16, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.45, ease: 'power2.out', stagger: 0.05 },
    )
  }, [filtered])

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            Your plays
          </div>
          <h1 className={styles.title}>Tickets</h1>
        </div>
        <Link to="/add">
          <Button variant="primary" size="sm">
            + Add ticket
          </Button>
        </Link>
      </div>

      {/* FILTERS */}
      <div className={styles.filters}>
        <div className={styles.chipRow}>
          <Pill tone={gameFilter === null ? 'mint' : 'muted'} onClick={() => setGameFilter(null)}>
            All games
          </Pill>
          {presentGames.map((k) => (
            <GameChip
              key={k}
              gameKey={k}
              size="sm"
              active={gameFilter === k}
              onClick={() => setGameFilter(gameFilter === k ? null : k)}
            />
          ))}
        </div>
        <div className={styles.segment} role="tablist" aria-label="Status filter">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={status === tab.key}
              className={`${styles.segBtn} ${status === tab.key ? styles.segBtnActive : ''}`}
              onClick={() => setStatus(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p style={{ color: 'var(--muted)' }}>Loading tickets…</p>}
      {isError && <p style={{ color: 'var(--loss)' }}>Could not load tickets.</p>}

      {/* EMPTY STATE */}
      {data && tickets.length === 0 && (
        <div className={styles.empty}>
          <span className={styles.emptyStar} aria-hidden>
            ★
          </span>
          <div>
            <div className={styles.emptyTitle}>No tickets yet</div>
            <p className={styles.emptySub}>
              Add your first play — scan a printed ticket or enter the numbers by hand.
            </p>
          </div>
          <Link to="/add">
            <Button variant="primary">Add your first ticket</Button>
          </Link>
        </div>
      )}

      {/* NO MATCHES for current filter */}
      {data && tickets.length > 0 && filtered.length === 0 && (
        <p style={{ color: 'var(--muted)' }}>No tickets match these filters.</p>
      )}

      {/* LIST */}
      {filtered.length > 0 && (
        <div className={styles.list} ref={listRef}>
          {filtered.map((t) => {
            const meta = gameMeta(t.game_key)
            const shownLines = t.lines.slice(0, 3)
            return (
              <div
                key={t.id}
                className={styles.card}
                data-reveal
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/tickets/${t.id}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    navigate(`/tickets/${t.id}`)
                  }
                }}
              >
                <div className={styles.cardHead}>
                  <GameChip gameKey={t.game_key} size="sm" />
                  <span className={styles.date}>{t.purchase_date}</span>
                  <span className={styles.method}>
                    {t.entry_method === 'ocr' ? '⛶ Scan' : '✎ Manual'}
                  </span>
                </div>

                <div className={styles.linesCol}>
                  {shownLines.map((line) => (
                    <BallRow
                      key={line.id}
                      main={line.main_numbers}
                      special={line.special_number}
                      size="sm"
                      pad={meta.isDaily4 ? 1 : 0}
                    />
                  ))}
                  {t.lines.length > shownLines.length && (
                    <span className={styles.moreLines}>+{t.lines.length - shownLines.length} more lines</span>
                  )}
                </div>

                <div className={styles.right}>
                  <ResultBadge t={t} />
                  <span className={styles.cost}>
                    Spent <Money cents={t.total_cost_cents} />
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
