import { useMemo, useState } from 'react'
import { useAuth } from '../lib/auth'
import {
  createDraw,
  createInvite,
  ingestResults,
  rematchResults,
  type IngestSummary,
} from '../lib/api'
import { GAMES, gameMeta } from '../lib/games'
import { Panel } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import { GameChip } from '../components/ui/GameChip'
import styles from './Admin.module.css'

function errText(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

function now(): string {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function Admin() {
  const { user } = useAuth()

  if (user && user.role !== 'admin') {
    return (
      <div className={styles.page}>
        <Panel eyebrow="Back office" title="Admins only">
          <p className={styles.note}>
            This area is reserved for administrators. If you think you should have access, ask the
            person who invited you.
          </p>
        </Panel>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          Back office
        </div>
        <h1 className={styles.title}>Admin</h1>
      </div>

      <InviteSection />
      <IngestSection />
      <DrawSection />
      <MatchSection />
    </div>
  )
}

/* -------------------------------------------------------------- Invite --- */

function InviteSection() {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setBusy(true)
    setErr(null)
    setToken(null)
    setCopied(false)
    try {
      const res = await createInvite(email.trim())
      setToken(res.token)
    } catch (e2) {
      setErr(errText(e2, 'Could not create the invite. Check the email and try again.'))
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    if (!token) return
    try {
      await navigator.clipboard.writeText(token)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      // clipboard blocked — user can still select the text manually
    }
  }

  return (
    <Panel eyebrow="Grow the room" title="Invite a player">
      <form className={styles.form} onSubmit={submit}>
        <div className={styles.row}>
          <div className={`${styles.field} ${styles.grow}`}>
            <label className={styles.label} htmlFor="invite-email">
              Player email
            </label>
            <input
              id="invite-email"
              type="email"
              className={styles.input}
              placeholder="player@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Creating…' : 'Create invite'}
          </Button>
        </div>
        {err && <div className={styles.err}>{err}</div>}
        {token && (
          <div className={styles.field}>
            <span className={styles.label}>Invite token</span>
            <div className={styles.tokenRow}>
              <div className={styles.tokenField} title={token}>
                {token}
              </div>
              <Button type="button" variant="brass" onClick={copy}>
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
            <p className={styles.note}>Share this token so they can register.</p>
          </div>
        )}
      </form>
    </Panel>
  )
}

/* -------------------------------------------------------------- Ingest --- */

interface LogEntry {
  time: string
  text: string
}

function summarize(s: IngestSummary): string {
  const games =
    typeof s.games_ingested === 'number'
      ? s.games_ingested
      : typeof (s as Record<string, unknown>).games === 'number'
        ? ((s as Record<string, unknown>).games as number)
        : undefined
  const draws = typeof s.draws_created === 'number' ? s.draws_created : undefined
  const results = typeof s.results_created === 'number' ? s.results_created : undefined
  const parts: string[] = []
  if (games !== undefined) parts.push(`${games} games`)
  if (draws !== undefined) parts.push(`${draws} draws`)
  if (results !== undefined) parts.push(`${results} results`)
  return parts.length ? parts.join(' · ') : 'Pipeline complete.'
}

function IngestSection() {
  const [busy, setBusy] = useState(false)
  const [log, setLog] = useState<LogEntry[]>([])
  const [err, setErr] = useState<string | null>(null)

  async function run() {
    setBusy(true)
    setErr(null)
    setLog((l) => [{ time: now(), text: 'Running results pipeline…' }, ...l])
    try {
      const summary = await ingestResults()
      setLog((l) => [{ time: now(), text: summarize(summary) }, ...l])
    } catch (e) {
      setErr(errText(e, 'The ingest failed. Try again or record draws manually below.'))
      setLog((l) => [{ time: now(), text: 'Ingest failed.' }, ...l])
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel
      eyebrow="Daily job"
      title="Run daily results"
      action={
        <Button variant="primary" onClick={run} disabled={busy}>
          {busy ? 'Running…' : 'Run now'}
        </Button>
      }
    >
      <p className={styles.note}>
        Scrapes the latest draws, ingests them, and matches your tickets against the results.
      </p>
      {err && <div className={styles.err} style={{ marginTop: 12 }}>{err}</div>}
      {log.length > 0 && (
        <div className={styles.log}>
          {log.map((e, i) => (
            <div key={i} className={styles.logRow}>
              <span className={styles.logTime}>{e.time}</span>
              <span>{e.text}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

/* ---------------------------------------------------------------- Draw --- */

function DrawSection() {
  const gameKeys = Object.keys(GAMES)
  const [gameKey, setGameKey] = useState(gameKeys[0])
  const meta = useMemo(() => gameMeta(gameKey), [gameKey])

  const [drawDate, setDrawDate] = useState(today())
  const [main, setMain] = useState<string[]>([])
  const [special, setSpecial] = useState('')
  const [multiplier, setMultiplier] = useState('')
  const [period, setPeriod] = useState('')

  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  // Reset numbers when the game (and its main count) changes.
  const mainCount = meta.mainCount
  const mainValues = useMemo(() => {
    const arr = main.slice(0, mainCount)
    while (arr.length < mainCount) arr.push('')
    return arr
  }, [main, mainCount])

  function setMainAt(i: number, v: string) {
    setMain((prev) => {
      const next = prev.slice(0, mainCount)
      while (next.length < mainCount) next.push('')
      next[i] = v.replace(/[^\d]/g, '')
      return next
    })
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    setOk(null)
    const winning_main = mainValues.map((v) => Number(v)).filter((n) => !Number.isNaN(n))
    if (winning_main.length !== mainCount) {
      setErr(`Enter all ${mainCount} winning numbers.`)
      return
    }
    setBusy(true)
    try {
      const res = await createDraw({
        game_key: gameKey,
        draw_date: drawDate,
        winning_main,
        winning_special: meta.hasSpecial && special !== '' ? Number(special) : null,
        multiplier: multiplier !== '' ? Number(multiplier) : null,
        draw_period: meta.isDaily4 && period !== '' ? period : null,
      })
      setOk(
        `Recorded ${meta.name} for ${res.draw.draw_date} — ${res.results_created} result${
          res.results_created === 1 ? '' : 's'
        } created.`,
      )
      setMain([])
      setSpecial('')
      setMultiplier('')
      setPeriod('')
    } catch (e2) {
      setErr(errText(e2, 'Could not record that draw. Check the numbers and try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel eyebrow="Manual fallback" title="Record a draw">
      <p className={styles.note}>Use this when a scrape fails and you need to key a draw by hand.</p>
      <form className={styles.form} onSubmit={submit} style={{ marginTop: 14 }}>
        <div className={styles.field}>
          <span className={styles.label}>Game</span>
          <div className={styles.gameChips}>
            {gameKeys.map((k) => (
              <GameChip
                key={k}
                gameKey={k}
                size="sm"
                active={k === gameKey}
                onClick={() => {
                  setGameKey(k)
                  setMain([])
                  setSpecial('')
                  setPeriod('')
                }}
              />
            ))}
          </div>
        </div>

        <div className={styles.row}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="draw-date">
              Draw date
            </label>
            <input
              id="draw-date"
              type="date"
              className={styles.input}
              value={drawDate}
              onChange={(e) => setDrawDate(e.target.value)}
              required
            />
          </div>
          {meta.isDaily4 && (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="draw-period">
                Period
              </label>
              <select
                id="draw-period"
                className={`${styles.input} ${styles.select}`}
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              >
                <option value="">—</option>
                <option value="morning">Morning</option>
                <option value="day">Day</option>
                <option value="evening">Evening</option>
                <option value="night">Night</option>
              </select>
            </div>
          )}
        </div>

        <div className={styles.field}>
          <span className={styles.label}>
            Winning numbers ({meta.mainMin}–{meta.mainMax})
          </span>
          <div className={styles.numRow}>
            {mainValues.map((v, i) => (
              <input
                key={i}
                className={styles.numInput}
                inputMode="numeric"
                value={v}
                onChange={(e) => setMainAt(i, e.target.value)}
                aria-label={`Winning number ${i + 1}`}
              />
            ))}
            {meta.hasSpecial && (
              <input
                className={`${styles.numInput} ${styles.special}`}
                inputMode="numeric"
                value={special}
                onChange={(e) => setSpecial(e.target.value.replace(/[^\d]/g, ''))}
                aria-label="Special number"
                placeholder="★"
              />
            )}
          </div>
        </div>

        <div className={styles.field} style={{ maxWidth: 200 }}>
          <label className={styles.label} htmlFor="draw-mult">
            Multiplier (optional)
          </label>
          <input
            id="draw-mult"
            className={styles.input}
            inputMode="numeric"
            placeholder="e.g. 2"
            value={multiplier}
            onChange={(e) => setMultiplier(e.target.value.replace(/[^\d]/g, ''))}
          />
        </div>

        {err && <div className={styles.err}>{err}</div>}
        {ok && (
          <div className={styles.ok}>
            <span aria-hidden>✓</span>
            <span>{ok}</span>
          </div>
        )}

        <div>
          <Button type="submit" variant="brass" disabled={busy}>
            {busy ? 'Recording…' : 'Record draw'}
          </Button>
        </div>
      </form>
    </Panel>
  )
}

/* --------------------------------------------------------------- Match --- */

function MatchSection() {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function run() {
    setBusy(true)
    setErr(null)
    setMsg(null)
    try {
      const res = await rematchResults()
      setMsg(
        `${res.results_created} new result${res.results_created === 1 ? '' : 's'} matched.`,
      )
    } catch (e) {
      setErr(errText(e, 'Re-matching failed. Try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel
      eyebrow="Reconcile"
      title="Re-run matching"
      action={
        <Button variant="ghost" onClick={run} disabled={busy}>
          {busy ? 'Matching…' : 'Re-run'}
        </Button>
      }
    >
      <p className={styles.note}>
        Re-checks every ticket against known draws — useful after keying a draw manually.
      </p>
      {err && <div className={styles.err} style={{ marginTop: 12 }}>{err}</div>}
      {msg && (
        <div className={styles.ok} style={{ marginTop: 12 }}>
          <span aria-hidden>✓</span>
          <span>{msg}</span>
        </div>
      )}
    </Panel>
  )
}
