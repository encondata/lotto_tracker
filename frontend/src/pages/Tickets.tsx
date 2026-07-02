import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchTickets } from '../lib/api'
import { PageStub } from './PageStub'
import { Panel } from '../components/ui/Panel'
import { GameChip } from '../components/ui/GameChip'
import { BallRow } from '../components/ui/Ball'
import { Money } from '../components/ui/Money'
import { Pill } from '../components/ui/Pill'
import { gameMeta } from '../lib/games'

export default function Tickets() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['tickets'],
    queryFn: fetchTickets,
  })

  return (
    <PageStub eyebrow="Your plays" title="Tickets">
      <Panel eyebrow="Ledger" title="All tickets">
        {isLoading && <p style={{ color: 'var(--muted)', margin: 0 }}>Loading tickets…</p>}
        {isError && (
          <p style={{ color: 'var(--loss)', margin: 0 }}>Could not load tickets.</p>
        )}
        {data && data.length === 0 && (
          <p style={{ color: 'var(--muted)', margin: 0 }}>No tickets yet.</p>
        )}
        {data && data.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {data.map((t) => {
              const meta = gameMeta(t.game_key)
              const line = t.lines[0]
              return (
                <Link
                  key={t.id}
                  to={`/tickets/${t.id}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    padding: '12px 14px',
                    border: '1px solid var(--line)',
                    borderRadius: 'var(--r-sm)',
                    background: 'var(--ink-2)',
                    flexWrap: 'wrap',
                  }}
                >
                  <GameChip gameKey={t.game_key} size="sm" />
                  {line && (
                    <BallRow
                      main={line.main_numbers}
                      special={line.special_number}
                      size="sm"
                      pad={meta.isDaily4 ? 1 : 0}
                    />
                  )}
                  <span style={{ marginLeft: 'auto', display: 'flex', gap: 14, alignItems: 'center' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--muted)' }}>
                      {t.purchase_date}
                    </span>
                    {t.total_won_cents > 0 ? (
                      <Pill tone="brass">
                        Won <Money cents={t.total_won_cents} />
                      </Pill>
                    ) : (
                      <Money cents={t.total_cost_cents} tone />
                    )}
                  </span>
                </Link>
              )
            })}
          </div>
        )}
      </Panel>
    </PageStub>
  )
}
