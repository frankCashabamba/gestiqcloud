import React from 'react'
import { Link, Outlet, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function TenantShell() {
  const { logout } = useAuth()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  return (
    <div>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, padding: '12px 16px' }}>
        <Link to={prefix || '/'} style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)', padding: '8px 12px', borderRadius: 8, textDecoration: 'none', color: 'inherit' }}>Inicio</Link>
        <button onClick={logout} style={{ border: 0, background: 'var(--color-primary)', color: 'var(--color-on-primary)', padding: '8px 12px', borderRadius: 8 }}>Cerrar sesión</button>
      </header>
      <Outlet />
    </div>
  )
}

