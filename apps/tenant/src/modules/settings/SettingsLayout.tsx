import React, { useMemo } from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'

type NavItem = {
  key: SettingsSection
  labelKey: string
  descKey: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { key: 'general', labelKey: 'settings:nav.general', descKey: 'settings:nav.generalDesc', path: 'general' },
  { key: 'branding', labelKey: 'settings:nav.branding', descKey: 'settings:nav.brandingDesc', path: 'branding' },
  { key: 'fiscal', labelKey: 'settings:nav.fiscal', descKey: 'settings:nav.fiscalDesc', path: 'fiscal' },
  { key: 'operativo', labelKey: 'settings:nav.operative', descKey: 'settings:nav.operativeDesc', path: 'operativo' },
  { key: 'horarios', labelKey: 'settings:nav.horarios', descKey: 'settings:nav.horariosDesc', path: 'horarios' },
  { key: 'notificaciones', labelKey: 'settings:nav.notificaciones', descKey: 'settings:nav.notificacionesDesc', path: 'notificaciones' },
  { key: 'modulos', labelKey: 'settings:nav.modulos', descKey: 'settings:nav.modulosDesc', path: 'modulos' },
  { key: 'avanzado', labelKey: 'settings:nav.avanzado', descKey: 'settings:nav.avanzadoDesc', path: 'avanzado' },
]

// Extra nav items that don't go through the permission guard
const EXTRA_NAV_ITEMS = [
  { path: 'receipt-template', label: 'Ticket POS', desc: 'Template impresora térmica' },
  { path: 'branches', label: 'Sucursales', desc: 'Gestión de puntos de venta' },
  { path: 'subscription', label: 'Suscripción', desc: 'Plan y facturación' },
  { path: 'security', label: 'Seguridad (MFA)', desc: 'Autenticación de dos factores' },
]

export default function SettingsLayout() {
  const { t } = useTranslation(['settings', 'common'])
  const { empresa } = useParams()
  const { canAccessSection, limitsLoading, isCompanyAdmin, multiUserPlan } = useSettingsAccess()
  const base = `/${empresa}/settings`

  const items = useMemo(
    () => NAV_ITEMS.filter((item) => canAccessSection(item.key)),
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
                  <div>{item.label}</div>
                  <div className="text-xs text-slate-500">{item.desc}</div>
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
