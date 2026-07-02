import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import gsap from 'gsap'
import { useAuth } from '../lib/auth'
import { Button } from '../components/ui/Button'
import styles from './Login.module.css'

const DrawStudio = lazy(() => import('../three/DrawStudio'))

export default function Login() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const cardRef = useRef<HTMLFormElement>(null)

  const [email, setEmail] = useState('demo@lottotracker.io')
  const [password, setPassword] = useState('demo12345')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  useEffect(() => {
    if (!cardRef.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    gsap.fromTo(
      cardRef.current,
      { y: 24, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.7, ease: 'power3.out' },
    )
  }, [])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch {
      setError('Sign-in failed. Check your email and password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.scene}>
        <Suspense fallback={null}>
          <DrawStudio numbers={[7, 11, 23, 42, 56, 19]} height="100vh" />
        </Suspense>
      </div>
      <div className={styles.glow} />

      <form ref={cardRef} className={styles.card} onSubmit={onSubmit}>
        <div className={styles.brand}>
          <span className={styles.star} aria-hidden>
            ★
          </span>
          <span className={styles.brandText}>Lone Star — Lotto Ledger</span>
        </div>

        <h1 className={styles.title}>The draw room</h1>
        <p className={styles.subtitle}>Sign in to open your ledger.</p>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className={styles.input}
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className={styles.input}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <Button type="submit" block disabled={submitting}>
          {submitting ? 'Entering…' : 'Enter'}
        </Button>

        <div className={styles.hint}>Demo — demo@lottotracker.io / demo12345</div>
      </form>
    </div>
  )
}
