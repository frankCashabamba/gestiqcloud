import React, { useEffect, useState } from 'react'
import { Link, Outlet, useLocation, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import SessionKeepAlive from '@shared/ui'
import { fetchCompanyTheme, invalidateCompanyThemeCache } from '../services/theme'

const SESSION_WARN_AFTER_MS = 9 * 60_000
const SESSION_RESPONSE_WINDOW_MS = 60_000

export default function CompanyShell() {
  const { logout } = useAuth()
  const useAuthHook = useAuth
  const { empresa } = useParams()
  const location = useLocation()
  const prefix = empresa ? `/${empresa}` : ''
  const year = new Date().getFullYear()
  const [brand, setBrand] = useState<{ name?: string; logoUrl?: string | null }>({})

  const isPosRoute = location.pathname.endsWith('/pos') || location.pathname.includes('/pos/')

  useEffect(() => {
    let mounted = true
    const loadTheme = async () => {
      try {
        const t = await fetchCompanyTheme(empresa)
        if (mounted && t?.brand) setBrand({ name: t.brand.name, logoUrl: t.brand.logoUrl })
      } catch {}
    }
    const onThemeUpdated = () => {
      invalidateCompanyThemeCache(empresa)
      void loadTheme()
    }
    void loadTheme()
    window.addEventListener('gc-theme-updated', onThemeUpdated)
    return () => {
      mounted = false
      window.removeEventListener('gc-theme-updated', onThemeUpdated)
    }
  }, [empresa])

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <SessionKeepAlive
        useAuth={useAuthHook as any}
        warnAfterMs={SESSION_WARN_AFTER_MS}
        responseWindowMs={SESSION_RESPONSE_WINDOW_MS}
      />

      {!isPosRoute && (
        <header className="gc-topbar">
          <div className="gc-container gc-topbar-inner">
            <Link to={prefix || '/'} className="gc-brand" title="Ir al panel principal">
              {brand.logoUrl ? <img src={brand.logoUrl} alt={brand.name || 'Logo'} className="h-7 w-auto" /> : null}
              <span className="gc-brand__name" title={brand.name || 'GestiqCloud'}>
                {brand.name || 'GestiqCloud'}
              </span>
            </Link>
            <nav className="gc-topbar-nav">
              <Link
                to={prefix || '/'}
                className="gc-button gc-button--ghost hidden lg:inline-flex"
                title="Ir al inicio del tenant"
              >
                Panel Admin
              </Link>
              <button type="button" onClick={logout} className="gc-button gc-button--primary">
                Cerrar sesion
              </button>
            </nav>
          </div>
        </header>
      )}

      <main className="flex-1">
        <Outlet />
      </main>

      {!isPosRoute && (
        <footer className="border-t border-slate-200 bg-white/90">
          <div className="gc-container flex h-14 flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <span>GestiqCloud {year}. Todos los derechos reservados.</span>
            <span className="font-medium text-slate-400">ERP | CRM | Plataforma modular</span>
          </div>
        </footer>
      )}
    </div>
  )
}
