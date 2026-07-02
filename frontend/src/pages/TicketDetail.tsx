import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchTicket, deleteTicket, type Ticket, type TicketResult } from '../lib/api'
import { gameMeta } from '../lib/games'
import { Panel } from '../components/ui/Panel'
import { GameChip } from '../components/ui/GameChip'
import { BallRow } from '../components/ui/Ball'
import { Money } from '../components/ui/Money'
import { Pill } from '../components/ui/Pill'
import { Button } from '../components/ui/Button'
import styles from './TicketDetail.module.css'

const ADDON_LABEL: Record<string, string> = {
  power_play: 'Power Play',
  extra: 'Extra!',
  fireball: 'Fireball',
}

function prettyTier(tier: string): string {
  return tier
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Result for a given line index, if any. */
function resultForLine(t: Ticket, lineIndex: number): TicketResult | undefined {
  // Results align to lines by order when present; fall back to index.
  return t.results[lineIndex]
}

export default function TicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const { data: t, isLoading, isError, error } = useQuery({
    queryKey: ['ticket', id],
    queryFn: () => fetchTicket(id as string),
    enabled: !!id,
    retry: false,
  })

  const notFound =
    isError && (error as { response?: { status?: number } })?.response?.status === 404

  async function handleDelete() {
    if (!id) return
    setDeleting(true)
    try {
      await deleteTicket(id)
      qc.invalidateQueries({ queryKey: ['tickets'] })
      navigate('/tickets')
    } catch {
      setDeleting(false)
      setConfirming(false)
    }
  }

  if (isLoading) {
    return (
      <div className={styles.page}>
        <p style={{ color: 'var(--muted)' }}>Loading ticket…</p>
      </div>
    )
  }

  if (notFound || !t) {
    return (
      <div className={styles.page}>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          Play detail
        </div>
        <h1 style={{ fontSize: 'clamp(1.6rem, 4vw, 2.2rem)' }}>Ticket not found</h1>
        <p style={{ color: 'var(--muted)', maxWidth: 480 }}>
          This ticket doesn’t exist, or it isn’t yours. It may have been deleted.
        </p>
        <Link to="/tickets" className={styles.back}>
          <Button variant="ghost" size="sm">
            ← Back to tickets
          </Button>
        </Link>
      </div>
    )
  }

  const meta = gameMeta(t.game_key)
  const addOns = Object.entries(t.add_ons ?? {}).filter(([, v]) => v)

  return (
    <div className={styles.page}>
      <Link to="/tickets" className={styles.back}>
        <Button variant="ghost" size="sm">
          ← Back to tickets
        </Button>
      </Link>

      {/* HERO */}
      <div className={styles.hero} style={{ borderColor: meta.color }}>
        <div
          className={styles.heroGlow}
          style={{ background: `radial-gradient(600px 200px at 0% 0%, ${meta.color}, transparent 60%)` }}
        />
        <div className={styles.heroTop}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span className={styles.heroName}>{meta.name}</span>
            <Pill tone="muted">{t.entry_method === 'ocr' ? 'Scanned' : 'Manual'}</Pill>
          </div>
          <GameChip gameKey={t.game_key} size="sm" />
        </div>
        <div className={styles.heroMeta}>
          <Pill tone="muted">Purchased {t.purchase_date}</Pill>
          <Pill tone="muted">
            {t.num_draws} {t.num_draws === 1 ? 'draw' : 'draws'}
          </Pill>
          {addOns.map(([flag]) => (
            <Pill key={flag} tone="brass">
              {ADDON_LABEL[flag] ?? prettyTier(flag)}
            </Pill>
          ))}
        </div>
      </div>

      {/* TOTALS */}
      <div className={styles.totals}>
        <div className={styles.totalCard}>
          <div className={styles.totalLabel}>Total cost</div>
          <div className={styles.totalVal} style={{ color: 'var(--ivory)' }}>
            <Money cents={t.total_cost_cents} />
          </div>
        </div>
        <div className={styles.totalCard}>
          <div className={styles.totalLabel}>Total won</div>
          <div className={styles.totalVal} style={{ color: t.total_won_cents > 0 ? 'var(--brass)' : 'var(--muted)' }}>
            <Money cents={t.total_won_cents} />
          </div>
        </div>
      </div>

      {/* LINES */}
      <Panel eyebrow="Numbers played" title={`${t.lines.length} ${t.lines.length === 1 ? 'line' : 'lines'}`}>
        {t.lines.map((line, i) => {
          const res = resultForLine(t, i)
          return (
            <div key={line.id} className={styles.lineRow}>
              <div className={styles.lineLeft}>
                <span className={styles.lineIdx}>#{i + 1}</span>
                <BallRow
                  main={line.main_numbers}
                  special={line.special_number}
                  size="md"
                  pad={meta.isDaily4 ? 1 : 0}
                />
                {line.play_type && <span className={styles.lineTag}>{prettyTier(line.play_type)}</span>}
                {line.is_quick_pick && <span className={styles.lineTag} style={{ color: 'var(--mint)' }}>Quick pick</span>}
              </div>

              <div className={styles.lineResult}>
                {res ? (
                  res.status === 'won' ? (
                    <>
                      <Pill tone="brass">
                        Won&nbsp;<Money cents={res.amount_won_cents} />
                      </Pill>
                      <span className={styles.tierSub}>
                        {res.tier_key ? prettyTier(res.tier_key) : `${res.match_main_count} matched`}
                      </span>
                    </>
                  ) : res.status === 'pending' ? (
                    <Pill tone="muted">Pending</Pill>
                  ) : (
                    <>
                      <span className={styles.tier}>No win</span>
                      <span className={styles.tierSub}>
                        {res.match_main_count} match{res.match_special ? ' + special' : ''}
                      </span>
                    </>
                  )
                ) : (
                  <Pill tone="muted">Pending</Pill>
                )}
              </div>
            </div>
          )
        })}
      </Panel>

      {/* DELETE */}
      <div className={styles.deleteRow}>
        {confirming ? (
          <>
            <span className={styles.confirmText}>Delete this ticket permanently?</span>
            <Button variant="ghost" size="sm" onClick={() => setConfirming(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button
              variant="brass"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
              style={{ background: 'var(--loss)', color: '#2a0f08' }}
            >
              {deleting ? 'Deleting…' : 'Yes, delete'}
            </Button>
          </>
        ) : (
          <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
            Delete ticket
          </Button>
        )}
      </div>
    </div>
  )
}
