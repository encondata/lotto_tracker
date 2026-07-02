import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { Button } from './ui/Button'
import styles from './AppShell.module.css'

interface NavItem {
  to: string
  label: string
  icon: string // simple emoji-free svg path is overkill; use short glyphs
  end?: boolean
  adminOnly?: boolean
}

const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: 'M3 12l9-8 9 8v8a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z', end: true },
  { to: '/tickets', label: 'Tickets', icon: 'M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4z' },
  { to: '/add', label: 'Add Ticket', icon: 'M12 5v14M5 12h14' },
  { to: '/analytics', label: 'Analytics', icon: 'M4 20V10M10 20V4M16 20v-8M22 20h-20' },
  { to: '/admin', label: 'Admin', icon: 'M12 2l7 4v6c0 5-3 8-7 10-4-2-7-5-7-10V6z', adminOnly: true },
]

function Icon({ d }: { d: string }) {
  return (
    <svg
      className={styles.icon}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d={d} />
    </svg>
  )
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function AppShell() {
  const { user, logout } = useAuth()
  const isAdmin = user?.role === 'admin'

  return (
    <div className={styles.shell}>
      <aside className={styles.rail}>
        <div className={styles.brand}>
          <span className={styles.star} aria-hidden>
            ★
          </span>
          <span className={styles.brandText}>
            Lone ★ Star
            <br />
            Lotto Ledger
          </span>
        </div>

        <nav className={styles.nav} aria-label="Primary">
          {NAV.filter((n) => !n.adminOnly || isAdmin).map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.linkActive : ''}`
              }
            >
              <Icon d={n.icon} />
              <span>{n.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className={styles.userBlock}>
          <div className={styles.userRow}>
            <div className={styles.avatar}>{initials(user?.display_name ?? '?')}</div>
            <div style={{ minWidth: 0 }}>
              <div className={styles.userName}>{user?.display_name ?? '—'}</div>
              <div className={styles.userRole}>{user?.role ?? 'player'}</div>
            </div>
          </div>
          <Button variant="ghost" size="sm" block onClick={logout}>
            Log out
          </Button>
        </div>
      </aside>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
