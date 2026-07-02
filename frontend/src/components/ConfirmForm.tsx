import { useEffect, useMemo, useRef, useState } from 'react'
import gsap from 'gsap'
import { GAMES, gameMeta, type GameMeta } from '../lib/games'
import type { PlayLineIn, TicketCreate, AddOns } from '../lib/api'
import { GameChip } from './ui/GameChip'
import { Ball } from './ui/Ball'
import { Button } from './ui/Button'
import { formatCents } from './ui/Money'
import styles from './ConfirmForm.module.css'

/* ------------------------------------------------------------ cost rules --- */
// Mirror backend app/prizes/cost.py. Base price per line, in cents.
const BASE_PRICE: Record<string, number> = {
  powerball: 200,
  mega_millions: 500,
  lotto_texas: 100,
  texas_two_step: 100,
  daily4: 100,
}
// Per-line surcharge add-ons (jackpot games), matching LINE_SURCHARGE.
const LINE_SURCHARGE: Record<string, { flag: string; cents: number }> = {
  powerball: { flag: 'power_play', cents: 100 },
  lotto_texas: { flag: 'extra', cents: 100 },
}

// Which add-on toggle each game exposes.
const GAME_ADDON: Record<string, { flag: string; label: string }> = {
  powerball: { flag: 'power_play', label: 'Power Play' },
  lotto_texas: { flag: 'extra', label: 'Extra!' },
  daily4: { flag: 'fireball', label: 'Fireball' },
}

const DAILY4_WAGERS = [
  { cents: 50, label: '50¢' },
  { cents: 100, label: '$1' },
]

/* ------------------------------------------------------------- draft type -- */
export interface FormDraft {
  game_key: string
  purchase_date: string
  num_draws: number
  add_ons: AddOns
  lines: PlayLineIn[]
  entry_method: 'manual' | 'ocr'
  confidence?: Record<string, number>
  flags?: string[]
}

interface ConfirmFormProps {
  draft: FormDraft
  /** Lock the game selector (scan mode pre-fills a game). */
  lockGame?: boolean
  submitting?: boolean
  errorMessage?: string | null
  onSubmit: (body: TicketCreate) => void
}

/* -------------------------------------------------------- editable state --- */
interface EditLine {
  main: string[] // string so inputs can be empty while typing
  special: string
  play_type: string
  wager_cents: number
  is_quick_pick: boolean
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function emptyLine(meta: GameMeta): EditLine {
  return {
    main: Array.from({ length: meta.mainCount }, () => ''),
    special: '',
    play_type: meta.playTypes?.[0] ?? '',
    wager_cents: meta.isDaily4 ? 100 : BASE_PRICE[meta.key] ?? 0,
    is_quick_pick: false,
  }
}

function lineFromDraft(meta: GameMeta, l: PlayLineIn): EditLine {
  const main = Array.from({ length: meta.mainCount }, (_, i) =>
    l.main_numbers[i] != null ? String(l.main_numbers[i]) : '',
  )
  return {
    main,
    special: l.special_number != null ? String(l.special_number) : '',
    play_type: l.play_type ?? meta.playTypes?.[0] ?? '',
    wager_cents: l.wager_cents && l.wager_cents > 0 ? l.wager_cents : meta.isDaily4 ? 100 : BASE_PRICE[meta.key] ?? 0,
    is_quick_pick: !!l.is_quick_pick,
  }
}

/* ---------------------------------------------------------- validation ----- */
function validateLine(meta: GameMeta, line: EditLine): string | null {
  const nums = line.main.map((s) => (s === '' ? NaN : Number(s)))
  if (nums.some((n) => Number.isNaN(n))) {
    return `Fill all ${meta.mainCount} numbers`
  }
  if (meta.isDaily4) {
    if (nums.some((n) => n < 0 || n > 9 || !Number.isInteger(n))) {
      return 'Digits must be 0–9'
    }
    if (!line.play_type) return 'Choose a play type'
  } else {
    if (nums.some((n) => n < meta.mainMin || n > meta.mainMax || !Number.isInteger(n))) {
      return `Numbers must be ${meta.mainMin}–${meta.mainMax}`
    }
    if (new Set(nums).size !== nums.length) return 'Numbers must be distinct'
    if (meta.hasSpecial) {
      const sp = line.special === '' ? NaN : Number(line.special)
      if (Number.isNaN(sp)) return 'Add the special ball'
      if (sp < (meta.specialMin ?? 1) || sp > (meta.specialMax ?? 99)) {
        return `Special must be ${meta.specialMin}–${meta.specialMax}`
      }
    }
  }
  return null
}

/* ---------------------------------------------------------------- confidence */
function confColor(c: number): string {
  if (c >= 0.9) return 'var(--mint)'
  if (c >= 0.75) return 'var(--brass)'
  return 'var(--loss)'
}

function ConfidenceDot({ value }: { value: number }) {
  return (
    <span className={styles.conf} title={`OCR confidence ${Math.round(value * 100)}%`}>
      <span className={styles.confDot} style={{ background: confColor(value) }} />
      {Math.round(value * 100)}%
    </span>
  )
}

/* ============================================================= component ==== */
export function ConfirmForm({
  draft,
  lockGame = false,
  submitting = false,
  errorMessage,
  onSubmit,
}: ConfirmFormProps) {
  const [gameKey, setGameKey] = useState(draft.game_key)
  const meta = gameMeta(gameKey)

  const [purchaseDate, setPurchaseDate] = useState(draft.purchase_date || today())
  const [numDraws, setNumDraws] = useState(Math.max(1, draft.num_draws || 1))
  const [addOns, setAddOns] = useState<AddOns>(draft.add_ons ?? {})
  const [lines, setLines] = useState<EditLine[]>(() =>
    draft.lines.length ? draft.lines.map((l) => lineFromDraft(meta, l)) : [emptyLine(meta)],
  )

  const confidence = draft.confidence ?? {}
  const flags = draft.flags ?? []
  const flaggedSet = useMemo(() => new Set(flags.map((f) => f.toLowerCase())), [flags])
  const isFlagged = (field: string) =>
    flaggedSet.has(field) || flags.some((f) => f.toLowerCase().includes(field.toLowerCase()))

  // When the game changes in manual mode, reset lines/add-ons for the new game.
  const prevGame = useRef(gameKey)
  useEffect(() => {
    if (prevGame.current === gameKey) return
    prevGame.current = gameKey
    const m = gameMeta(gameKey)
    setLines([emptyLine(m)])
    setAddOns({})
  }, [gameKey])

  const addonCfg = GAME_ADDON[gameKey]

  /* --------------------------------------------------------- cost preview -- */
  const totalCost = useMemo(() => {
    const draws = Math.max(1, numDraws)
    if (meta.isDaily4) {
      const fireball = !!addOns.fireball
      let total = 0
      for (const l of lines) {
        let c = l.wager_cents || BASE_PRICE.daily4
        if (fireball) c *= 2
        total += c
      }
      return total * draws
    }
    let perLine = BASE_PRICE[gameKey] ?? 0
    const sur = LINE_SURCHARGE[gameKey]
    if (sur && addOns[sur.flag]) perLine += sur.cents
    return perLine * lines.length * draws
  }, [meta.isDaily4, gameKey, lines, addOns, numDraws])

  /* ---------------------------------------------------------- validation --- */
  const lineErrors = lines.map((l) => validateLine(meta, l))
  const isValid = lineErrors.every((e) => e === null) && lines.length > 0

  /* ------------------------------------------------------------- mutators -- */
  function setMain(li: number, ni: number, val: string) {
    const clean = val.replace(/[^0-9]/g, '').slice(0, 2)
    setLines((prev) =>
      prev.map((l, i) => (i === li ? { ...l, main: l.main.map((m, j) => (j === ni ? clean : m)) } : l)),
    )
  }
  function setSpecial(li: number, val: string) {
    const clean = val.replace(/[^0-9]/g, '').slice(0, 2)
    setLines((prev) => prev.map((l, i) => (i === li ? { ...l, special: clean } : l)))
  }
  function patchLine(li: number, patch: Partial<EditLine>) {
    setLines((prev) => prev.map((l, i) => (i === li ? { ...l, ...patch } : l)))
  }
  function addLine() {
    setLines((prev) => [...prev, emptyLine(meta)])
  }
  function removeLine(li: number) {
    setLines((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== li)))
  }
  function toggleAddon(flag: string) {
    setAddOns((prev) => ({ ...prev, [flag]: !prev[flag] }))
  }

  /* --------------------------------------------------------------- submit -- */
  const formRef = useRef<HTMLFormElement>(null)
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isValid || submitting) return
    const body: TicketCreate = {
      game_key: gameKey,
      purchase_date: purchaseDate,
      num_draws: Math.max(1, numDraws),
      add_ons: addonCfg ? { [addonCfg.flag]: !!addOns[addonCfg.flag] } : {},
      entry_method: draft.entry_method,
      lines: lines.map((l) => ({
        main_numbers: l.main.map((s) => Number(s)),
        special_number: meta.hasSpecial ? Number(l.special) : null,
        play_type: meta.isDaily4 ? l.play_type : null,
        wager_cents: meta.isDaily4 ? l.wager_cents : BASE_PRICE[gameKey] ?? 0,
        is_quick_pick: l.is_quick_pick,
      })),
    }
    onSubmit(body)
  }

  // Reveal animation on the lines block.
  useEffect(() => {
    if (!formRef.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const rows = formRef.current.querySelectorAll('[data-reveal]')
    gsap.fromTo(
      rows,
      { y: 14, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.45, ease: 'power2.out', stagger: 0.06 },
    )
  }, [])

  const playTypeLabel = (pt: string) =>
    pt
      .split('-')
      .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
      .join(' ')

  return (
    <form className={styles.form} onSubmit={handleSubmit} ref={formRef}>
      {flags.length > 0 && (
        <div className={styles.flagsNotice} data-reveal>
          <span aria-hidden style={{ fontSize: '1.1rem' }}>
            ⚠
          </span>
          <div>
            <strong>Double-check the highlighted fields.</strong>
            <ul>
              {flags.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {errorMessage && <div className={styles.formError}>{errorMessage}</div>}

      {/* GAME */}
      <div className={styles.section} data-reveal>
        <div className={styles.label}>
          Game
          {confidence.game_key != null && <> · <ConfidenceDot value={confidence.game_key} /></>}
        </div>
        <div className={styles.gameChips}>
          {lockGame ? (
            <GameChip gameKey={gameKey} active />
          ) : (
            Object.keys(GAMES).map((k) => (
              <GameChip key={k} gameKey={k} active={k === gameKey} onClick={() => setGameKey(k)} />
            ))
          )}
        </div>
      </div>

      {/* DATE + DRAWS */}
      <div className={styles.metaRow} data-reveal>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="purchase-date">
            Purchase date
            {confidence.purchase_date != null && <> · <ConfidenceDot value={confidence.purchase_date} /></>}
          </label>
          <input
            id="purchase-date"
            type="date"
            className={`${styles.input} ${isFlagged('date') ? styles.flagged : ''}`}
            value={purchaseDate}
            max={today()}
            onChange={(e) => setPurchaseDate(e.target.value)}
          />
        </div>
        <div className={styles.field}>
          <span className={styles.label}>Draws</span>
          <div className={styles.stepper}>
            <button
              type="button"
              className={styles.stepBtn}
              onClick={() => setNumDraws((n) => Math.max(1, n - 1))}
              disabled={numDraws <= 1}
              aria-label="Fewer draws"
            >
              −
            </button>
            <span className={styles.stepVal}>{numDraws}</span>
            <button
              type="button"
              className={styles.stepBtn}
              onClick={() => setNumDraws((n) => n + 1)}
              aria-label="More draws"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* ADD-ONS */}
      {addonCfg && (
        <div className={styles.section} data-reveal>
          <div className={styles.label}>Add-ons</div>
          <div className={styles.toggles}>
            <button
              type="button"
              className={`${styles.toggle} ${addOns[addonCfg.flag] ? styles.toggleOn : ''} ${
                isFlagged('add_on') || isFlagged(addonCfg.flag) ? styles.toggleFlagged : ''
              }`}
              onClick={() => toggleAddon(addonCfg.flag)}
              aria-pressed={!!addOns[addonCfg.flag]}
            >
              <span className={`${styles.switch} ${addOns[addonCfg.flag] ? styles.switchOn : ''}`}>
                <span className={styles.knob} />
              </span>
              {addonCfg.label}
            </button>
          </div>
        </div>
      )}

      {/* PLAY LINES */}
      <div className={styles.section} data-reveal>
        <div className={styles.label}>Play lines</div>
        <div className={styles.lines}>
          {lines.map((line, li) => {
            const err = lineErrors[li]
            const lineFlagged = isFlagged(`line_${li}`) || isFlagged(`line ${li}`)
            const filledMain = line.main.map((s) => s !== '' && !Number.isNaN(Number(s)))
            return (
              <div key={li} className={`${styles.line} ${lineFlagged ? styles.lineFlagged : ''}`}>
                <div className={styles.lineHead}>
                  <span className={styles.lineTitle}>
                    Line {li + 1}
                    {confidence[`line_${li}`] != null && <ConfidenceDot value={confidence[`line_${li}`]} />}
                    {line.is_quick_pick && <span style={{ color: 'var(--mint)' }}>QP</span>}
                  </span>
                  <button
                    type="button"
                    className={styles.removeBtn}
                    onClick={() => removeLine(li)}
                    disabled={lines.length <= 1}
                    aria-label={`Remove line ${li + 1}`}
                  >
                    ×
                  </button>
                </div>

                {/* number inputs */}
                <div className={styles.numRow}>
                  {line.main.map((val, ni) => (
                    <input
                      key={ni}
                      type="text"
                      inputMode="numeric"
                      className={`${styles.numInput} ${filledMain[ni] ? styles.filled : ''}`}
                      value={val}
                      placeholder={meta.isDaily4 ? '0' : '—'}
                      onChange={(e) => setMain(li, ni, e.target.value)}
                      aria-label={`Line ${li + 1} number ${ni + 1}`}
                    />
                  ))}
                  {meta.hasSpecial && (
                    <>
                      <span className={styles.specialSep} aria-hidden>
                        +
                      </span>
                      <input
                        type="text"
                        inputMode="numeric"
                        className={`${styles.numInput} ${styles.special}`}
                        value={line.special}
                        placeholder="★"
                        onChange={(e) => setSpecial(li, e.target.value)}
                        aria-label={`Line ${li + 1} special ball`}
                      />
                    </>
                  )}
                </div>

                {/* live ball preview */}
                <div className={styles.linePreview}>
                  {filledMain.some(Boolean) || line.special ? (
                    <>
                      {line.main.map((s, ni) =>
                        filledMain[ni] ? (
                          <Ball
                            key={ni}
                            number={Number(s)}
                            size="sm"
                            pad={meta.isDaily4 ? 1 : 0}
                          />
                        ) : null,
                      )}
                      {meta.hasSpecial && line.special !== '' && (
                        <Ball number={Number(line.special)} variant="special" size="sm" />
                      )}
                    </>
                  ) : (
                    <span className={styles.hint}>
                      {meta.isDaily4
                        ? 'Enter 4 digits (0–9)'
                        : `Enter ${meta.mainCount} numbers ${meta.mainMin}–${meta.mainMax}`}
                    </span>
                  )}
                </div>

                {/* daily4 controls + quick pick */}
                <div className={styles.lineControls}>
                  {meta.isDaily4 && (
                    <>
                      <select
                        className={styles.select}
                        value={line.play_type}
                        onChange={(e) => patchLine(li, { play_type: e.target.value })}
                        aria-label={`Line ${li + 1} play type`}
                      >
                        {meta.playTypes?.map((pt) => (
                          <option key={pt} value={pt}>
                            {playTypeLabel(pt)}
                          </option>
                        ))}
                      </select>
                      <select
                        className={styles.select}
                        value={line.wager_cents}
                        onChange={(e) => patchLine(li, { wager_cents: Number(e.target.value) })}
                        aria-label={`Line ${li + 1} wager`}
                      >
                        {DAILY4_WAGERS.map((w) => (
                          <option key={w.cents} value={w.cents}>
                            {w.label}
                          </option>
                        ))}
                      </select>
                    </>
                  )}
                  <button
                    type="button"
                    className={`${styles.toggle} ${line.is_quick_pick ? styles.toggleOn : ''}`}
                    onClick={() => patchLine(li, { is_quick_pick: !line.is_quick_pick })}
                    aria-pressed={line.is_quick_pick}
                  >
                    <span className={`${styles.switch} ${line.is_quick_pick ? styles.switchOn : ''}`}>
                      <span className={styles.knob} />
                    </span>
                    Quick pick
                  </button>
                </div>

                {err && <div className={styles.lineError}>{err}</div>}
              </div>
            )
          })}
        </div>
        <Button type="button" variant="ghost" size="sm" className={styles.addLine} onClick={addLine}>
          + Add line
        </Button>
      </div>

      {/* FOOTER */}
      <div className={styles.footer} data-reveal>
        <div className={styles.cost}>
          <span className={styles.costLabel}>Total cost</span>
          <span className={styles.costVal}>{formatCents(totalCost)}</span>
        </div>
        <Button type="submit" variant="primary" disabled={!isValid || submitting}>
          {submitting ? 'Saving…' : 'Save ticket'}
        </Button>
      </div>
    </form>
  )
}
