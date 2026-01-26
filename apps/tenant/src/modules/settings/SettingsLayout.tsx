import React, { useMemo } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'

type NavItem = {
  key: SettingsSection
  label: string
  desc: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { key: 'general', label: 'General', desc: 'Datos base de la empresa', path: 'general' },
  { key: 'branding', label: 'Branding', desc: 'Logo y color primario', path: 'branding' },
  { key: 'fiscal', label: 'Fiscal', desc: 'RUC y regimen', path: 'fiscal' },
  { key: 'operativo', label: 'Operativo', desc: 'POS e inventario', path: 'operativo' },
  { key: 'horarios', label: 'Horarios', desc: 'Apertura y cierre', path: 'horarios' },
  { key: 'notificaciones', label: 'Notificaciones', desc: 'Canales y alertas', path: 'notificaciones' },
  { key: 'modulos', label: 'Modulos', desc: 'Activar o desactivar', path: 'modulos' },
  { key: 'avanzado', label: 'Avanzado', desc: 'JSON y ajustes finos', path: 'avanzado' },
]

export default function SettingsLayout() {
  const { canAccessSection, limitsLoading, isCompanyAdmin, multiUserPlan } = useSettingsAccess()

  const items = useMemo(
    () => NAV_ITEMS.filter((item) => canAccessSection(item.key)),
    [canAccessSection]
  )

  return (
    <div className="p-4 md:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Configuracion</h1>
        <p className="text-sm text-slate-600">
          Configura el tenant por areas. Algunas secciones pueden estar ocultas segun tu rol.
        </p>
        {!isCompanyAdmin && !limitsLoading && !multiUserPlan && (
          <div className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
            Tu plan no tiene multiples usuarios. Solo un admin puede gestionar settings completos.
          </div>
        )}
      </div>

      {limitsLoading ? (
        <div className="text-sm text-slate-500">Loading permissions...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6">
          <aside className="border rounded-lg bg-white">
            <nav className="p-3 space-y-1">
              <NavLink
                to="."
                end
                className={({ isActive }) =>
                  `block rounded px-3 py-2 text-sm ${isActive ? 'bg-slate-100 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`
                }
              >
                Resumen
              </NavLink>
              {items.map((item) => (
                <NavLink
                  key={item.key}
                  to={item.path}
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
