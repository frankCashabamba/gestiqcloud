import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'

type Card = {
  key: SettingsSection
  label: string
  desc: string
  path: string
}

const GROUPS: { title: string; items: Card[] }[] = [
  {
    title: 'Empresa',
    items: [
      { key: 'general', label: 'General', desc: 'Datos basicos del negocio', path: 'general' },
      { key: 'branding', label: 'Branding', desc: 'Logo y colores', path: 'branding' },
      { key: 'fiscal', label: 'Fiscal', desc: 'RUC y regimen', path: 'fiscal' },
    ],
  },
  {
    title: 'Operacion',
    items: [
      { key: 'operativo', label: 'Operativo', desc: 'POS e inventario', path: 'operativo' },
      { key: 'horarios', label: 'Horarios', desc: 'Apertura y cierre', path: 'horarios' },
    ],
  },
  {
    title: 'Comunicaciones',
    items: [
      { key: 'notificaciones', label: 'Notificaciones', desc: 'Email, WhatsApp, Telegram', path: 'notificaciones' },
    ],
  },
  {
    title: 'Plan y control',
    items: [
      { key: 'modulos', label: 'Modulos', desc: 'Activar o desactivar', path: 'modulos' },
      { key: 'avanzado', label: 'Avanzado', desc: 'JSON e integraciones', path: 'avanzado' },
    ],
  },
]

export default function SettingsHome() {
  const { canAccessSection } = useSettingsAccess()

  const groups = useMemo(() => {
    return GROUPS.map((group) => ({
      ...group,
      items: group.items.filter((item) => canAccessSection(item.key)),
    })).filter((group) => group.items.length > 0)
  }, [canAccessSection])

  return (
    <div className="p-4 md:p-6">
      <div className="grid gap-6">
        {groups.map((group) => (
          <section key={group.title}>
            <h2 className="text-sm font-semibold text-slate-700 mb-3">{group.title}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {group.items.map((item) => (
                <Link
                  key={item.key}
                  to={item.path}
                  className="border rounded-lg p-4 hover:border-slate-300 hover:bg-slate-50 transition"
                >
                  <div className="font-semibold">{item.label}</div>
                  <div className="text-sm text-slate-600">{item.desc}</div>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
