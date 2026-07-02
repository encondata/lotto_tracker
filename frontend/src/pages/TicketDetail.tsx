import { useParams, Link } from 'react-router-dom'
import { PageStub } from './PageStub'
import { Panel } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'

export default function TicketDetail() {
  const { id } = useParams()
  return (
    <PageStub eyebrow="Play detail" title={`Ticket #${id ?? ''}`}>
      <Panel eyebrow="Studio note" title="Coming in the next pass">
        <p style={{ color: 'var(--muted)', marginTop: 0, maxWidth: 560 }}>
          A full breakdown for ticket <span className="mono">{id}</span> — lines, draws, and
          per-tier results — arrives in a later pass.
        </p>
        <Link to="/tickets">
          <Button variant="ghost" size="sm">
            ← Back to tickets
          </Button>
        </Link>
      </Panel>
    </PageStub>
  )
}
