import React from 'react'

interface ModuleCardProps {
  module: {
    id: string
    name: string
    icon: string
    enabled: boolean
    description?: string
    category?: string
  }
  onToggle: (moduleId: string, enabled: boolean) => void
  onClick: (moduleId: string) => void
}

export default function ModuleCard({ module, onToggle, onClick }: ModuleCardProps) {
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    onToggle(module.id, !module.enabled)
  }

  return (
    <div
      onClick={() => onClick(module.id)}
      className={`
        relative p-5 rounded-lg border-2 transition-all cursor-pointer
        hover:shadow-lg hover:-translate-y-1
        ${module.enabled 
          ? 'border-green-500 bg-green-50' 
          : 'border-gray-300 bg-gray-50 opacity-75'
        }
      `}
    >
      {/* Badge Estado */}
      <div className="absolute top-3 right-3">
        <span
          className={`
            px-2 py-1 text-xs font-semibold rounded-full
            ${module.enabled 
              ? 'bg-green-600 text-white' 
              : 'bg-gray-400 text-white'
            }
          `}
        >
          {module.enabled ? '✓ ACTIVO' : '⊗ INACTIVO'}
        </span>
      </div>

      {/* Icono */}
      <div className="flex items-center mb-3">
        <div className="text-4xl mr-3">{module.icon}</div>
        <div>
          <h3 className="font-semibold text-lg text-gray-800">
            {module.name}
          </h3>
          {module.category && (
            <p className="text-xs text-gray-500 uppercase">
              {module.category}
            </p>
          )}
        </div>
      </div>

      {/* Descripción */}
      {module.description && (
        <p className="text-sm text-gray-600 mb-4 min-h-[40px]">
          {module.description}
        </p>
      )}

      {/* Toggle Switch */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-200">
        <span className="text-sm font-medium text-gray-700">
          {module.enabled ? 'Desactivar' : 'Activar'}
        </span>
        <button
          onClick={handleToggle}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full
            transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2
            ${module.enabled 
              ? 'bg-green-600 focus:ring-green-500' 
              : 'bg-gray-300 focus:ring-gray-400'
            }
          `}
          aria-label={`Toggle ${module.name}`}
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white transition-transform
              ${module.enabled ? 'translate-x-6' : 'translate-x-1'}
            `}
          />
        </button>
      </div>

      {/* Click overlay */}
      <div className="absolute inset-0 rounded-lg hover:bg-black hover:bg-opacity-5 pointer-events-none" />
    </div>
  )
}
