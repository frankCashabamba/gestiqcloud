import React, { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import SectorLayout from './components/SectorLayout'
import { useMisModulos } from '../hooks/useMisModulos'

function buildSlug(name?: string, url?: string, slug?: string): string {
  if (slug) return slug.toLowerCase()
  if (url) {
    const normalized = url.startsWith('/') ? url.slice(1) : url
    const segment = normalized.split('/')[0] || normalized
    return segment.toLowerCase()
  }
  return (name || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/['-?]/g, '')
    .replace(/\s+/g, '')
}

const kpiCard = (key: string, title: string, helper: string) => (
  <article key={key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
    <p className="mt-3 text-2xl font-semibold text-slate-900">--</p>
    <p className="mt-2 text-[11px] text-slate-400">{helper}</p>
  </article>
)

const DefaultPlantilla: React.FC<{ slug?: string }> = ({ slug }) => {
  const { t } = useTranslation()
  const { modules, allowedSlugs } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''

  const sideNav = useMemo(
    () =>
      [...modules]
        .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
        .map((m) => ({
          label: m.name || buildSlug(m.name, m.url, m.slug),
          to: `/${buildSlug(m.name, m.url, m.slug)}`,
        })),
    [modules]
  )

  const quickAccess = useMemo(() => sideNav.slice(0, 6), [sideNav])

  const kpis = useMemo(() => {
    const items: React.ReactNode[] = []
    if (allowedSlugs.has('ventas')) {
      items.push(kpiCard('sales', t('defaultDashboard.kpis.sales.title'), t('defaultDashboard.kpis.sales.help')))
    }
    if (allowedSlugs.has('gastos')) {
      items.push(kpiCard('expenses', t('defaultDashboard.kpis.expenses.title'), t('defaultDashboard.kpis.expenses.help')))
    }
    if (allowedSlugs.has('facturacion')) {
      items.push(kpiCard('invoices', t('defaultDashboard.kpis.invoices.title'), t('defaultDashboard.kpis.invoices.help')))
    }
    if (!items.length) {
      items.push(kpiCard('placeholder', t('defaultDashboard.kpis.placeholder.title'), t('defaultDashboard.kpis.placeholder.help')))
    }
    return items
  }, [allowedSlugs, t])

  const recommended = useMemo(() => sideNav.slice(0, 4), [sideNav])

  return (
    <SectorLayout
      title={t('defaultDashboard.title')}
      subtitle={t('defaultDashboard.subtitle')}
      topNav={sideNav.slice(0, 3)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
        <section className="gc-card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {t('defaultDashboard.welcome')}{slug ? ` · ${slug}` : ''}
            </h2>
            <p className="mt-2 text-sm text-slate-500">{t('defaultDashboard.welcomeHelp')}</p>
          </div>

          {quickAccess.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('defaultDashboard.quickAccess')}</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {quickAccess.map((item) => (
                  <Link
                    key={item.to}
                    to={`${prefix}${item.to}`}
                    className="group flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
                  >
                    <span>{item.label}</span>
                    <span className="text-xs text-slate-400 transition group-hover:text-blue-600">{t('defaultDashboard.openModule')}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 p-4">
            <h3 className="text-sm font-semibold text-slate-700">{t('defaultDashboard.personalizeTitle')}</h3>
            <p className="mt-2 text-sm text-slate-500">{t('defaultDashboard.personalizeHelp')}</p>
          </div>
        </section>

        <aside className="gc-card-muted space-y-4">
          <h3 className="text-sm font-semibold text-slate-700">{t('defaultDashboard.nextSteps')}</h3>
          <ul className="space-y-3 text-sm text-slate-500">
            <li>{t('defaultDashboard.nextStepsItems.branding')}</li>
            <li>{t('defaultDashboard.nextStepsItems.banking')}</li>
            <li>{t('defaultDashboard.nextStepsItems.owners')}</li>
          </ul>

          {recommended.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('defaultDashboard.highlightedModules')}</h4>
              <div className="mt-3 space-y-2">
                {recommended.map((item) => (
                  <Link
                    key={item.to}
                    to={`${prefix}${item.to}`}
                    className="block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 transition hover:border-blue-200 hover:text-blue-700"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </SectorLayout>
  )
}

export default DefaultPlantilla
