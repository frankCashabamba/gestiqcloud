import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { useMisModulos } from '../hooks/useMisModulos'
import { getMiEmpresa, type Empresa } from '../services/empresa'

export default function Dashboard() {
  const { t } = useTranslation()
  const { profile } = useAuth()
  const { modules, loading, error } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  const [empresaInfo, setEmpresaInfo] = useState<Empresa | null>(null)
  useEffect(() => { getMiEmpresa().then(arr => setEmpresaInfo(arr[0] || null)).catch(()=>{}) }, [])

  return (
    <div className="gc-container py-8">
      <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-[var(--gc-muted)]">
        <span>{t('pages.dashboard.companyLabel')} <strong className="font-semibold text-[var(--gc-foreground)]">{empresaInfo?.name || empresa || '—'}</strong></span>
        <span>{t('pages.dashboard.userLabel')} <strong className="font-semibold text-[var(--gc-foreground)]">{profile?.username || profile?.user_id || '—'}</strong></span>
      </div>

      <header className="gc-page-header mb-8">
        <div className="gc-page-header__text">
          <h1 className="gc-page-header__title">
            {t('pages.dashboard.contractedModules')} {(!loading && modules.length > 0) ? `(${modules.length})` : ''}
          </h1>
        </div>
      </header>

      {loading && (
        <div className="gc-empty">
          <div className="gc-empty__icon">⏳</div>
          <p className="gc-empty__text">{t('pages.dashboard.loadingModules')}</p>
        </div>
      )}

      {!loading && modules.length === 0 && (
        <div className="gc-empty">
          <div className="gc-empty__icon">📦</div>
          <p className="gc-empty__title">{t('pages.dashboard.noModules')}</p>
        </div>
      )}

      {!loading && modules.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {[...modules].sort((a, b) => (a.name || '').localeCompare(b.name || '')).map((m) => {
            const to = prefix + (m.url || `/${(m.name || '').toLowerCase()}`)
            return (
              <Link key={m.id} to={to} className="gc-module-card">
                <div className="gc-module-card__icon">
                  {(m.name || '?')[0].toUpperCase()}
                </div>
                <div className="gc-module-card__text">
                  <div className="gc-module-card__name">{m.name}</div>
                  <div className="gc-module-card__desc">{m.categoria || t('dashboard.moduleFallback')}</div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
