import React from 'react'
import { Link, useParams } from 'react-router-dom'

type NavItem = { label: string; to: string }

type Props = {
  title: string
  topNav?: NavItem[]
  sideNav?: NavItem[]
  kpis?: React.ReactNode
  children?: React.ReactNode
}

const linkStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '8px 12px',
  borderRadius: 8,
  color: 'inherit',
  textDecoration: 'none',
}

export default function SectorLayout({ title, topNav = [], sideNav = [], kpis, children }: Props) {
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 16px' }}>
      <a href="#main" style={{ position: 'absolute', left: -9999, top: 'auto' }} onFocus={(e)=>{ e.currentTarget.style.left = '8px' }} onBlur={(e)=>{ e.currentTarget.style.left = '-9999px' }}>Saltar al contenido</a>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 0', gap: 12 }}>
        <h1 style={{ margin: 0 }}>{title}</h1>
        {topNav.length > 0 && (
          <nav aria-label="Acciones rápidas">
            {topNav.map((n) => (
              <Link key={n.to} to={`${prefix}${n.to}`} style={{ ...linkStyle, marginLeft: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>{n.label}</Link>
            ))}
          </nav>
        )}
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 16 }}>
        <aside aria-label="Navegación de módulo" style={{ border: '1px solid var(--color-border)', borderRadius: 12, background: 'var(--color-surface)', padding: 8 }}>
          <nav>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {sideNav.map((n) => (
                <li key={n.to}>
                  <Link to={`${prefix}${n.to}`} style={{ display: 'block', padding: '10px 12px', borderRadius: 8, color: 'inherit', textDecoration: 'none' }} className="side-link">{n.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <main id="main" role="main">
          {kpis && (
            <section aria-label="Indicadores clave" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 16 }}>
              {kpis}
            </section>
          )}
          <section aria-label="Contenido">
            {children}
          </section>
        </main>
      </div>
    </div>
  )
}

