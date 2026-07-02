import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import { AppShell } from './components/AppShell'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Tickets from './pages/Tickets'
import TicketDetail from './pages/TicketDetail'
import AddTicket from './pages/AddTicket'
import Analytics from './pages/Analytics'
import Admin from './pages/Admin'

function ProtectedLayout() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) {
    return (
      <div
        style={{
          display: 'grid',
          placeItems: 'center',
          minHeight: '100vh',
          color: 'var(--muted)',
        }}
      >
        <span className="mono">Opening the ledger…</span>
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <AppShell />
}

function AdminRoute() {
  const { user } = useAuth()
  if (user && user.role !== 'admin') return <Navigate to="/" replace />
  return <Admin />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/add" element={<AddTicket />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/admin" element={<AdminRoute />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
