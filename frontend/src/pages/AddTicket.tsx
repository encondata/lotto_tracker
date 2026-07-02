import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import gsap from 'gsap'
import {
  scanTicket,
  createTicket,
  type OcrDraft,
  type TicketCreate,
} from '../lib/api'
import { GAMES, gameMeta } from '../lib/games'
import { Panel } from '../components/ui/Panel'
import { GameChip } from '../components/ui/GameChip'
import { ConfirmForm, type FormDraft } from '../components/ConfirmForm'
import styles from './AddTicket.module.css'

type Mode = 'scan' | 'manual'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function reduced(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Build an empty draft for a manually chosen game. */
function emptyDraft(gameKey: string): FormDraft {
  const meta = gameMeta(gameKey)
  return {
    game_key: gameKey,
    purchase_date: today(),
    num_draws: 1,
    add_ons: {},
    entry_method: 'manual',
    lines: [
      {
        main_numbers: [],
        special_number: meta.hasSpecial ? null : null,
        play_type: meta.isDaily4 ? meta.playTypes?.[0] ?? null : null,
        wager_cents: meta.isDaily4 ? 100 : 0,
        is_quick_pick: false,
      },
    ],
  }
}

export default function AddTicket() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [mode, setMode] = useState<Mode>('scan')

  // scan state
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // shared confirm state
  const [draft, setDraft] = useState<FormDraft | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // manual game selection (before a game is chosen, no form shown)
  const [manualGame, setManualGame] = useState<string | null>(null)

  const shimmerRef = useRef<HTMLDivElement>(null)
  const confirmRef = useRef<HTMLDivElement>(null)

  // Shimmer sweep during scanning.
  useEffect(() => {
    if (!scanning || !shimmerRef.current || reduced()) return
    const tween = gsap.fromTo(
      shimmerRef.current,
      { xPercent: -100 },
      { xPercent: 100, duration: 1.1, ease: 'power1.inOut', repeat: -1 },
    )
    return () => {
      tween.kill()
    }
  }, [scanning])

  // Reveal the confirm form when a draft appears.
  useEffect(() => {
    if (!draft || !confirmRef.current || reduced()) return
    gsap.fromTo(
      confirmRef.current,
      { y: 20, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.5, ease: 'power2.out' },
    )
  }, [draft])

  function draftFromOcr(ocr: OcrDraft): FormDraft {
    return {
      game_key: ocr.game_key,
      purchase_date: ocr.purchase_date || today(),
      num_draws: ocr.num_draws || 1,
      add_ons: ocr.add_ons ?? {},
      lines: ocr.lines ?? [],
      entry_method: 'ocr',
      confidence: ocr.confidence ?? {},
      flags: ocr.flags ?? [],
    }
  }

  async function handleFile(file: File) {
    setScanError(null)
    setDraft(null)
    setScanning(true)
    // Give the shimmer a beat so it reads as "scanning".
    const started = Date.now()
    try {
      const ocr = await scanTicket(file)
      const elapsed = Date.now() - started
      if (elapsed < 700) await new Promise((r) => setTimeout(r, 700 - elapsed))
      setDraft(draftFromOcr(ocr))
    } catch {
      setScanError('Could not read that ticket. Try another photo or enter it manually.')
    } finally {
      setScanning(false)
    }
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  async function handleSubmit(body: TicketCreate) {
    setSubmitError(null)
    setSubmitting(true)
    try {
      const ticket = await createTicket(body)
      qc.invalidateQueries({ queryKey: ['tickets'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
      navigate(`/tickets/${ticket.id}`)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSubmitError(detail || 'Could not save the ticket. Check the fields and try again.')
      setSubmitting(false)
    }
  }

  function switchMode(next: Mode) {
    setMode(next)
    setDraft(null)
    setScanError(null)
    setSubmitError(null)
    setManualGame(null)
  }

  function resetScan() {
    setDraft(null)
    setScanError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className={styles.page}>
      <div>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          New play
        </div>
        <h1 className={styles.title}>Add ticket</h1>
      </div>

      {/* MODE SEGMENT */}
      <div className={styles.modeSeg} role="tablist" aria-label="Entry mode">
        <button
          role="tab"
          aria-selected={mode === 'scan'}
          className={`${styles.modeBtn} ${mode === 'scan' ? styles.modeBtnActive : ''}`}
          onClick={() => switchMode('scan')}
        >
          Scan
        </button>
        <button
          role="tab"
          aria-selected={mode === 'manual'}
          className={`${styles.modeBtn} ${mode === 'manual' ? styles.modeBtnActive : ''}`}
          onClick={() => switchMode('manual')}
        >
          Enter manually
        </button>
      </div>

      {/* SCAN MODE */}
      {mode === 'scan' && !draft && (
        <>
          {scanning ? (
            <div className={styles.scanning}>
              <div className={styles.shimmer} ref={shimmerRef} />
              <span className={styles.scanIcon} aria-hidden>
                ⛶
              </span>
              <span className={styles.scanText}>Reading your ticket…</span>
            </div>
          ) : (
            <>
              <div
                className={`${styles.dropzone} ${dragOver ? styles.dropzoneOver : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    fileInputRef.current?.click()
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
              >
                <span className={styles.dropIcon} aria-hidden>
                  📷
                </span>
                <span className={styles.dropTitle}>Snap or upload your ticket</span>
                <span className={styles.dropSub}>
                  Drop a photo here, or click to choose one. We’ll read the numbers for you.
                </span>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className={styles.hiddenInput}
                onChange={onInputChange}
              />
              {scanError && <p className={styles.scanError}>{scanError}</p>}
            </>
          )}
        </>
      )}

      {/* MANUAL MODE — pick a game first */}
      {mode === 'manual' && !manualGame && (
        <Panel eyebrow="Choose a game" title="Which game did you play?">
          <div className={styles.gamePickChips}>
            {Object.keys(GAMES).map((k) => (
              <GameChip
                key={k}
                gameKey={k}
                onClick={() => {
                  setManualGame(k)
                  setDraft(emptyDraft(k))
                }}
              />
            ))}
          </div>
        </Panel>
      )}

      {/* SHARED CONFIRM FORM */}
      {draft && (
        <div ref={confirmRef}>
          <Panel
            eyebrow={mode === 'scan' ? 'Confirm the scan' : 'Enter your numbers'}
            title={gameMeta(draft.game_key).name}
          >
            <ConfirmForm
              draft={draft}
              lockGame={mode === 'scan'}
              submitting={submitting}
              errorMessage={submitError}
              onSubmit={handleSubmit}
            />
          </Panel>
          {mode === 'scan' && (
            <button
              type="button"
              className={styles.modeBtn}
              style={{ marginTop: 12, border: '1px solid var(--line)' }}
              onClick={resetScan}
            >
              ← Scan a different ticket
            </button>
          )}
        </div>
      )}
    </div>
  )
}
