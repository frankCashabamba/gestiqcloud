import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { useMisModulos } from '../hooks/useMisModulos'
import { getMiEmpresa, type Empresa } from '../services/empresa'

const HIDDEN_SLUGS = new Set(['templates', 'webhooks', 'reports', 'copilot'])

export default function Dashboard() {
  const { t } = useTranslation()
  const { profile } = useAuth()
  const { modules, loading } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  const [empresaInfo, setEmpresaInfo] = useState<Empresa | null>(null)

  useEffect(() => {
    getMiEmpresa().then(arr => setEmpresaInfo(arr[0] || null)).catch(() => {})
  }, [])

  const username = profile?.username || profile?.user_id || null
  const companyName = empresaInfo?.name || empresa || '—'

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Buenos días' : hour < 19 ? 'Buenas tardes' : 'Buenas noches'

  const grouped = useMemo(() => {
    const visible = modules.filter(m => !HIDDEN_SLUGS.has(m.slug || ''))
    const acc: Record<string, typeof modules> = {}
    for (const m of visible) {
      const cat = (m.categoria || m.category || 'General').toString()
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(m)
    }
    // sort modules within each category alphabetically
    for (const cat of Object.keys(acc)) {
      acc[cat].sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    }
    return acc
  }, [modules])

  const sortedCategories = useMemo(() => Object.keys(grouped).sort((a, b) => a.localeCompare(b)), [grouped])

  return (
    <div className="gc-container py-8">
      {/* Welcome header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--gc-foreground)]">
          {greeting}{username ? `, ${username}` : ''}
        </h1>
        <p className="text-sm text-[var(--gc-muted)] mt-0.5">{companyName}</p>
      </div>

      {/* CTA to copilot */}
      <Link
        to={`${prefix}/copilot`}
        className="flex items-center justify-between w-full bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 py-4 mb-8 transition-colors"
      >
        <div>
          <p className="font-semibold text-base">Ver resumen del negocio</p>
          <p className="text-sm text-blue-100 mt-0.5">Ventas, stock, cobros y sugerencias con IA</p>
        </div>
        <span className="text-xl">→</span>
      </Link>

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

      {!loading && sortedCategories.length > 0 && (
        <div className="space-y-8">
          {sortedCategories.map(cat => (
            <div key={cat}>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--gc-muted)] mb-3">{cat}</p>
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {grouped[cat].map(m => {
                  const to = prefix + (m.url || `/${(m.slug || m.name || '').toLowerCase()}`)
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
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
