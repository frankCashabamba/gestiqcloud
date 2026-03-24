import React, { useMemo } from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSettingsAccess } from './useSettingsAccess'
import { SETTINGS_SECTIONS } from './sections'

// Nav keys map: section key → i18n suffix (operativo maps to 'operative' por legacy)
const NAV_KEY: Record<string, string> = { operativo: 'operative' }
const navKey = (key: string) => NAV_KEY[key] ?? key

// Extra nav items that don't go through the permission guard
const EXTRA_NAV_ITEMS = [
  { path: 'receipt-template', labelKey: 'settings:nav.receiptTemplate', descKey: 'settings:nav.receiptTemplateDesc' },
  { path: 'branches', labelKey: 'settings:nav.branches', descKey: 'settings:nav.branchesDesc' },
  { path: 'subscription', labelKey: 'settings:nav.subscription', descKey: 'settings:nav.subscriptionDesc' },
  { path: 'security', labelKey: 'settings:nav.security', descKey: 'settings:nav.securityDesc' },
]

export default function SettingsLayout() {
  const { t } = useTranslation(['settings', 'common'])
  const { empresa } = useParams()
  const { canAccessSection, limitsLoading, isCompanyAdmin, multiUserPlan } = useSettingsAccess()
  const base = `/${empresa}/settings`

  const items = useMemo(
    () =>
      SETTINGS_SECTIONS.filter((s) => canAccessSection(s.key)).map((s) => ({
        ...s,
        labelKey: `settings:nav.${navKey(s.key)}`,
        descKey: `settings:nav.${navKey(s.key)}Desc`,
      })),
    [canAccessSection]
  )

  return (
    <div className="p-4 md:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">{t('settings:layout.title')}</h1>
        <p className="text-sm text-slate-600">
          {t('settings:layout.subtitle')}
        </p>
        {!isCompanyAdmin && !limitsLoading && !multiUserPlan && (
          <div className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
            {t('settings:layout.planWarning')}
          </div>
        )}
      </div>

      {limitsLoading ? (
        <div className="text-sm text-slate-500">{t('settings:layout.loadingPermissions')}</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6">
          <aside className="border rounded-lg bg-white">
            <nav className="p-3 space-y-1">
              <NavLink
                to={base}
                end
                className={({ isActive }) =>
                  `block rounded px-3 py-2 text-sm ${isActive ? 'bg-slate-100 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`
                }
              >
                {t('settings:layout.summary')}
              </NavLink>
              {items.map((item) => (
                <NavLink
                  key={item.key}
                  to={`${base}/${item.path}`}
                  className={({ isActive }) =>
                    `block rounded px-3 py-2 text-sm ${isActive ? 'bg-slate-100 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`
                  }
                >
                  <div>{t(item.labelKey)}</div>
                  <div className="text-xs text-slate-500">{t(item.descKey)}</div>
                </NavLink>
              ))}
              <div className="my-2 border-t border-slate-100" />
              {EXTRA_NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.path}
                  to={`${base}/${item.path}`}
                  className={({ isActive }) =>
                    `block rounded px-3 py-2 text-sm ${isActive ? 'bg-slate-100 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`
                  }
                >
                  <div>{t(item.labelKey)}</div>
                  <div className="text-xs text-slate-500">{t(item.descKey)}</div>
                </NavLink>
              ))}
            </nav>
          </aside>

          <main className="border rounded-lg bg-white">
            <Outlet />
          </main>
        </div>
      )}
    </div>
  )
}
