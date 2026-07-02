import type { ReactNode } from 'react'
import { Panel } from '../components/ui/Panel'

interface PageStubProps {
  eyebrow: string
  title: string
  children?: ReactNode
}

export function PageStub({ eyebrow, title, children }: PageStubProps) {
  return (
    <div style={{ maxWidth: 1100 }}>
      <div className="eyebrow" style={{ marginBottom: 8 }}>
        {eyebrow}
      </div>
      <h1 style={{ fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', marginBottom: 24 }}>{title}</h1>
      {children ?? (
        <Panel eyebrow="Studio note" title="Coming in the next pass">
          <p style={{ color: 'var(--muted)', margin: 0, maxWidth: 560 }}>
            This room is being built. Routing, navigation, and the design system are wired up —
            the full experience lands in a later pass.
          </p>
        </Panel>
      )}
    </div>
  )
}
