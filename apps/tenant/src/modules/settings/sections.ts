import type { SettingsSection } from './useSettingsAccess'

export type SectionGroupKey = 'company' | 'operation' | 'communications' | 'planControl'

export type SettingsNestedItemKey =
  | 'users'
  | 'templates'
  | 'webhooks'
  | 'notificationCenter'
  | 'einvoicing'
  | 'reconciliation'

export const SETTINGS_SECTIONS: Array<{
  key: SettingsSection
  path: string
  group: SectionGroupKey
}> = [
  { key: 'general', path: 'general', group: 'company' },
  { key: 'branding', path: 'branding', group: 'company' },
  { key: 'fiscal', path: 'fiscal', group: 'company' },
  { key: 'operativo', path: 'operativo', group: 'operation' },
  { key: 'horarios', path: 'horarios', group: 'operation' },
  { key: 'notificaciones', path: 'notificaciones', group: 'communications' },
  { key: 'modulos', path: 'modulos', group: 'planControl' },
]

export const SECTION_GROUPS: Array<{ key: SectionGroupKey; titleKey: string }> = [
  { key: 'company', titleKey: 'settings:groups.company' },
  { key: 'operation', titleKey: 'settings:groups.operation' },
  { key: 'communications', titleKey: 'settings:groups.communications' },
  { key: 'planControl', titleKey: 'settings:groups.planControl' },
]

export const SETTINGS_NESTED_ITEMS: Array<{
  key: SettingsNestedItemKey
  path: string
  labelKey: string
  descKey: string
  moduleKey?: string
}> = [
  {
    key: 'users',
    path: 'users',
    labelKey: 'settings:nav.users',
    descKey: 'settings:nav.usersDesc',
    moduleKey: 'users',
  },
  {
    key: 'templates',
    path: 'templates',
    labelKey: 'settings:nav.templates',
    descKey: 'settings:nav.templatesDesc',
  },
  {
    key: 'webhooks',
    path: 'webhooks',
    labelKey: 'settings:nav.webhooks',
    descKey: 'settings:nav.webhooksDesc',
  },
  {
    key: 'notificationCenter',
    path: 'notification-center',
    labelKey: 'settings:nav.notificationCenter',
    descKey: 'settings:nav.notificationCenterDesc',
  },
  {
    key: 'einvoicing',
    path: 'einvoicing',
    labelKey: 'settings:nav.einvoicing',
    descKey: 'settings:nav.einvoicingDesc',
    moduleKey: 'einvoicing',
  },
  {
    key: 'reconciliation',
    path: 'reconciliation',
    labelKey: 'settings:nav.reconciliation',
    descKey: 'settings:nav.reconciliationDesc',
  },
]
