import type { SettingsSection } from './useSettingsAccess'

export type SectionGroupKey = 'company' | 'operation' | 'communications' | 'planControl'

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
