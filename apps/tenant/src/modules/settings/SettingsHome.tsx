import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSettingsAccess } from './useSettingsAccess'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import { SETTINGS_SECTIONS, SECTION_GROUPS } from './sections'

export default function SettingsHome() {
  const { t } = useTranslation(['settings', 'common'])
  const can = usePermission()
  const { canAccessSection } = useSettingsAccess()

  const groups = useMemo(() => {
    return SECTION_GROUPS.map((group) => ({
      titleKey: group.titleKey,
      items: SETTINGS_SECTIONS.filter(
        (s) => s.group === group.key && canAccessSection(s.key)
      ).map((s) => ({
        key: s.key,
        path: s.path,
        labelKey: `settings:cards.${s.key}.label`,
        descKey: `settings:cards.${s.key}.desc`,
      })),
    })).filter((group) => group.items.length > 0)
  }, [canAccessSection])

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
