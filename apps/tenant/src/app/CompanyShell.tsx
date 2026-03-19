import React, { lazy, Suspense, useEffect, useState } from 'react'
import { Link, Outlet, useLocation, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import SessionKeepAlive from '@shared/ui'
import { fetchCompanyTheme, invalidateCompanyThemeCache } from '../services/theme'

const CopilotChatWidget = lazy(() => import('../components/CopilotChatWidget'))

const SESSION_WARN_AFTER_MS = 9 * 60_000
const SESSION_RESPONSE_WINDOW_MS = 60_000

export default function CompanyShell() {
  const { logout, profile, loading } = useAuth()
  const { t } = useTranslation('common')
  const useAuthHook = useAuth
  const { empresa } = useParams()
  const location = useLocation()
  const prefix = empresa ? `/${empresa}` : ''
  const year = new Date().getFullYear()
  const [brand, setBrand] = useState<{ name?: string; logoUrl?: string | null }>({})

  // Detecta sesión de otro tenant: si el slug en la URL no coincide con el token activo, forzar logout
  useEffect(() => {
    if (loading || !empresa || !profile) return
    const tokenSlug = profile.empresa_slug
    if (tokenSlug && tokenSlug !== empresa) {
      invalidateCompanyThemeCache()
      logout().then(() => {
        window.location.replace(`/login`)
      })
    }
  }, [loading, empresa, profile?.empresa_slug])

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
            <Link to={prefix || '/'} className="gc-brand" title={t('shell.goToPanel')}>
              {brand.logoUrl ? (
                <img src={brand.logoUrl} alt={brand.name || 'Logo'} className="gc-brand__logo-img" />
              ) : (
                <span className="gc-brand__logo">{(brand.name || 'G').charAt(0).toUpperCase()}</span>
              )}
              <span className="gc-brand__name" title={brand.name || 'GestiqCloud'}>
                {brand.name || 'GestiqCloud'}
              </span>
            </Link>
            <nav className="gc-topbar-nav">
              <Link
                to={prefix || '/'}
                className="gc-button gc-button--ghost hidden lg:inline-flex"
                title={t('shell.goToHome')}
              >
                {t('shell.adminPanel')}
              </Link>
              <button type="button" onClick={logout} className="gc-button gc-button--primary">
                {t('shell.logout')}
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
            <span>{t('shell.copyright', { year })}</span>
            <span className="font-medium text-slate-400">{t('shell.tagline')}</span>
          </div>
        </footer>
      )}

      {!isPosRoute && (
        <Suspense fallback={null}>
          <CopilotChatWidget />
        </Suspense>
      )}
    </div>
  )
}
