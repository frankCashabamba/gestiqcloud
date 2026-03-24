import React from 'react'
import { useTranslation } from 'react-i18next'

interface ModuleCardProps {
  module: {
    id: string
    name: string
    icon: string
    enabled: boolean
    description?: string
    category?: string
    required?: boolean
    dependencies?: string[]
  }
  onToggle: (moduleId: string, enabled: boolean) => void
  onClick: (moduleId: string) => void
  disabled?: boolean
}

const badgeColors = {
  on: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  off: 'bg-gray-100 text-gray-600 border-gray-200'
}

export default function ModuleCard({ module, onToggle, onClick, disabled = false }: ModuleCardProps) {
  const { t } = useTranslation(['settings', 'common'])
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (disabled) return
    onToggle(module.id, !module.enabled)
  }

  return (
    <div
      onClick={() => onClick(module.id)}
      className={`
        relative p-5 rounded-xl border transition-all cursor-pointer bg-white
        shadow-sm hover:shadow-md hover:-translate-y-0.5
        ${module.enabled ? 'border-emerald-200' : 'border-gray-200'}
        ${disabled ? 'opacity-60 cursor-not-allowed' : ''}
      `}
    >
      {/* Estado */}
      <div className="absolute top-3 right-3 flex items-center gap-2">
        {module.required && (
          <span className="text-[11px] font-semibold px-2 py-1 rounded-full bg-amber-100 text-amber-700 border border-amber-200">
            {t('settings:modules.required')}
          </span>
        )}
        <span
          className={`text-[11px] font-semibold px-2 py-1 rounded-full border ${
            module.enabled ? badgeColors.on : badgeColors.off
          }`}
        >
          {module.enabled ? t('settings:modules.active') : t('settings:modules.inactive')}
        </span>
      </div>

      {/* Icono + título */}
      <div className="flex items-center gap-3 mb-3">
        <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center text-2xl">
          {module.icon || '📦'}
        </div>
        <div>
          <h3 className="font-semibold text-lg text-gray-900 leading-tight">{module.name}</h3>
          {module.category && (
            <p className="text-xs text-gray-500 uppercase tracking-wide">{module.category}</p>
          )}
        </div>
      </div>

      {/* Descripción */}
      {module.description && (
        <p className="text-sm text-gray-600 mb-4 line-clamp-3">{module.description}</p>
      )}

      {/* Dependencias */}
      {module.dependencies && module.dependencies.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {module.dependencies.map(dep => (
            <span
              key={dep}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full border border-gray-200"
            >
              {t('settings:modules.dependsOn', { dep })}
            </span>
          ))}
        </div>
      )}

      {/* Toggle */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div className="text-sm text-gray-700">
          {module.enabled ? t('settings:modules.disableToggle') : t('settings:modules.enableToggle')}
        </div>
        <button
          onClick={handleToggle}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none
            ${module.enabled ? 'bg-emerald-500' : 'bg-gray-300'}
          `}
          aria-label={`Toggle ${module.name}`}
          disabled={disabled || module.required}
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white transition-transform
              ${module.enabled ? 'translate-x-5' : 'translate-x-1'}
            `}
          />
        </button>
      </div>

      {/* Hover overlay */}
      <div className="absolute inset-0 rounded-xl pointer-events-none border border-transparent hover:border-blue-100" />
    </div>
  )
}
