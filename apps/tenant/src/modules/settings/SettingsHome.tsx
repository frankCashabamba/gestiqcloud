import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'

type Card = {
  key: SettingsSection
  labelKey: string
  descKey: string
  path: string
}

const GROUPS: { titleKey: string; items: Card[] }[] = [
  {
    titleKey: 'settings:groups.company',
    items: [
      { key: 'general', labelKey: 'settings:cards.general.label', descKey: 'settings:cards.general.desc', path: 'general' },
      { key: 'branding', labelKey: 'settings:cards.branding.label', descKey: 'settings:cards.branding.desc', path: 'branding' },
      { key: 'fiscal', labelKey: 'settings:cards.fiscal.label', descKey: 'settings:cards.fiscal.desc', path: 'fiscal' },
    ],
  },
  {
    titleKey: 'settings:groups.operation',
    items: [
      { key: 'operativo', labelKey: 'settings:cards.operativo.label', descKey: 'settings:cards.operativo.desc', path: 'operativo' },
      { key: 'horarios', labelKey: 'settings:cards.horarios.label', descKey: 'settings:cards.horarios.desc', path: 'horarios' },
    ],
  },
  {
    titleKey: 'settings:groups.communications',
    items: [
      { key: 'notificaciones', labelKey: 'settings:cards.notificaciones.label', descKey: 'settings:cards.notificaciones.desc', path: 'notificaciones' },
    ],
  },
  {
    titleKey: 'settings:groups.planControl',
    items: [
      { key: 'modulos', labelKey: 'settings:cards.modulos.label', descKey: 'settings:cards.modulos.desc', path: 'modulos' },
      { key: 'avanzado', labelKey: 'settings:cards.avanzado.label', descKey: 'settings:cards.avanzado.desc', path: 'avanzado' },
    ],
  },
]

export default function SettingsHome() {
  const { t } = useTranslation(['settings', 'common'])
  const can = usePermission()
  const { canAccessSection } = useSettingsAccess()

  const groups = useMemo(() => {
    return GROUPS.map((group) => ({
      ...group,
      items: group.items.filter((item) => canAccessSection(item.key)),
    })).filter((group) => group.items.length > 0)
  }, [canAccessSection, t])

  if (!can('settings:read')) {
    return <PermissionDenied permission="settings:read" />
  }

  return (
    <div className="p-4 md:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('settings:title')}</h1>
        <p className="text-gray-600 text-sm">{t('settings:subtitle')}</p>
      </div>
      <div className="grid gap-6">
        {groups.map((group) => (
          <section key={group.titleKey}>
            <h2 className="text-sm font-semibold text-slate-700 mb-3">{t(group.titleKey)}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {group.items.map((item) => (
                 <Link
                   key={item.key}
                   to={item.path}
                   className="border rounded-lg p-4 hover:border-slate-300 hover:bg-slate-50 transition"
                 >
                   <div className="font-semibold">{t(item.labelKey)}</div>
                   <div className="text-sm text-slate-600">{t(item.descKey)}</div>
                 </Link>
               ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
