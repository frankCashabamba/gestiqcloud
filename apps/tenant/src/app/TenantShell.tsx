import React from 'react'
import { Link, Outlet, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import SessionKeepAlive from '@shared/ui'
import { env } from '../env'

const SESSION_WARN_AFTER_MS = 9 * 60_000
const SESSION_RESPONSE_WINDOW_MS = 60_000

export default function TenantShell() {
  const { logout } = useAuth()
  const useAuthHook = useAuth
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  const year = new Date().getFullYear()

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <SessionKeepAlive useAuth={useAuthHook as any} warnAfterMs={SESSION_WARN_AFTER_MS} responseWindowMs={SESSION_RESPONSE_WINDOW_MS} />

      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="gc-container flex h-16 items-center justify-between">
          <Link to={prefix || '/'} className="text-sm font-semibold text-slate-700 transition hover:text-blue-600">
            GestiqCloud
          </Link>
          <nav className="flex items-center gap-3">
            <Link to={prefix || '/'} className="gc-button gc-button--ghost hidden sm:inline-flex" title="Ir al inicio del tenant">
              Panel Admin
            </Link>
            <button type='button' onClick={logout} className="gc-button gc-button--primary">
              Cerrar sesión
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white/90">
        <div className="gc-container flex h-14 flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span>© GestiqCloud {year}. Todos los derechos reservados.</span>
          <span className="font-medium text-slate-400">ERP · CRM · Plataforma modular</span>
        </div>
      </footer>
    </div>
  )
}

