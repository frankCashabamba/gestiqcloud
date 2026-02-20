
import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../../auth/AuthContext'
import { isCompanyAdmin } from '../utils/companyAdmin'

type ImportadorLayoutProps = {
  title?: string
  description?: string
  actions?: React.ReactNode
  children: React.ReactNode
}

function buildBasePath(pathname: string) {
  // Buscar prefijo del módulo: /importador, /imports o /importer (alias en EN)
  // Puede venir como /:empresa/importer/preview/products, etc.
  const match = pathname.match(/^(.*?\/(?:importador|imports|importer))(?:\/|$)/)
  if (match && match[1]) return match[1]
  // Fallback: quita trailing slash
  return pathname.replace(/\/$/, '')
}

function joinPath(base: string, segment: string) {
  if (segment === '.' || segment === '') return base
  const cleanBase = base.replace(/\/$/, '')
  const cleanSegment = segment.replace(/^\//, '')
  return `${cleanBase}/${cleanSegment}`
}

export default function ImportadorLayout({
  title = 'Data Importer',
  description = 'Upload files, review batches, and manage pending items in one place.',
  actions,
  children,
}: ImportadorLayoutProps) {
  const location = useLocation()
  const basePath = buildBasePath(location.pathname)
  const { t } = useTranslation()
  const { profile, token } = useAuth()
  const canManageImporterSettings = isCompanyAdmin(profile, token)

  const navItems = React.useMemo(() => ([
    { to: '.', label: t('importerNav.import') },
    { to: 'preview', label: t('importerNav.preview') },
    { to: 'batches', label: t('importerNav.batches') },
    { to: 'products', label: t('importerNav.products') },
    ...(canManageImporterSettings ? [{ to: 'settings', label: t('importerNav.settings') }] : []),
  ]), [t, canManageImporterSettings])

  return (
    <div className="gc-container gc-stack pb-12">
      <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              {t('importerLayout.badge')}
            </span>
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
              {description && <p className="mt-2 max-w-3xl text-sm text-slate-500">{description}</p>}
            </div>
          </div>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
        <nav className="mt-6 flex flex-wrap gap-2">
          {navItems.map((item) => {
            const target = joinPath(basePath, item.to === '.' ? '' : item.to)
            return (
              <NavLink
                key={item.to}
                to={target}
                end={item.to === '.'}
                className={({ isActive }) =>
                  `rounded-xl px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </header>
      <main className="gc-stack">{children}</main>
    </div>
  )
}
