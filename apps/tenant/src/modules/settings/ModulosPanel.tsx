import React, { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import ModuleCard from './components/ModuleCard'
import ModuleConfigForm from './components/ModuleConfigForm'
import { useToast, getErrorMessage } from '../../shared/toast'
import {
  listAvailableModules,
  enableModule,
  disableModule,
  getModuleSettings,
  updateModuleSettings
} from '../../services/api/settings'

interface Module {
  id: string
  name: string
  icon: string
  description: string
  category: string
  enabled: boolean
  required?: boolean
  config?: any
  dependencies?: string[]
}

const CATEGORY_LABELS: Record<string, string> = {
  sales: 'Ventas',
  operations: 'Operaciones',
  finance: 'Finanzas',
  people: 'RRHH',
  analytics: 'Analítica',
  config: 'Configuración',
  core: 'Core'
}

export default function ModulosPanel() {
  const { t } = useTranslation()
  const [modules, setModules] = useState<Module[]>([])
  const [selectedModule, setSelectedModule] = useState<Module | null>(null)
  const [activeTab, setActiveTab] = useState<string>('Todos')
  const [loading, setLoading] = useState<boolean>(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [savingModuleId, setSavingModuleId] = useState<string | null>(null)
  const { success, error, warning } = useToast()

  // Cargar módulos desde la BBDD para reflejar el estado real del cliente
  const loadModules = useCallback(async () => {
    setLoading(true)
    setFetchError(null)
    try {
      const response = await listAvailableModules()
      const apiModules: any[] = Array.isArray(response?.modules)
        ? response.modules
        : Array.isArray(response)
          ? response
          : []

      const normalized = apiModules.map((m: any): Module => ({
        id: m.id || m.code,
        name: m.name,
        icon: m.icon || '📦',
        description: m.description,
        category: CATEGORY_LABELS[m.category] || m.category || 'Otros',
        enabled: Boolean(m.is_enabled ?? m.enabled ?? m.default_enabled),
        required: Boolean(m.required),
        dependencies: m.dependencies || [],
        config: m.config || {}
      }))

      // Respeta la configuración guardada en la base: no mostrar módulos marcados como inactivos
      setModules(normalized.filter(m => m.enabled || normalized.length === 0))
    } catch (e: any) {
      const message = getErrorMessage(e)
      setFetchError(message)
      error(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadModules()

  }, [])

  // Categorías únicas
  const categories = ['Todos', ...Array.from(new Set(modules.map(m => m.category)))]

  // Filtrar módulos por categoría
  const filteredModules = activeTab === 'Todos'
    ? modules
    : modules.filter(m => m.category === activeTab)

  // Toggle módulo con persistencia en BBDD
  const handleToggle = async (moduleId: string, enabled: boolean) => {
    const module = modules.find(m => m.id === moduleId)
    if (!module) return

    if (module.required && module.enabled && !enabled) {
      warning('Este módulo es obligatorio y no puede desactivarse')
      return
    }

    setSavingModuleId(moduleId)
    try {
      if (enabled) {
        await enableModule(moduleId)
      } else {
        await disableModule(moduleId)
      }

      setModules(prev => prev.map(m =>
        m.id === moduleId ? { ...m, enabled } : m
      ))

      success(`Módulo ${module.name} ${enabled ? 'activado' : 'desactivado'}`)
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSavingModuleId(null)
    }
  }

  // Abrir configuración: se lee del backend en tiempo real
  const handleClickModule = async (moduleId: string) => {
    const module = modules.find(m => m.id === moduleId)
    if (!module) return

    try {
      const configResponse = await getModuleSettings(moduleId)
      const config =
        (configResponse && (configResponse.config || configResponse.module_config)) || {}
      setSelectedModule({ ...module, config })
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  // Guardar configuración de módulo
  const handleSaveConfig = async (moduleId: string, config: any) => {
    try {
      await updateModuleSettings(moduleId, config)
      setModules(prev => prev.map(m =>
        m.id === moduleId ? { ...m, config } : m
      ))
    } catch (e: any) {
      error(getErrorMessage(e))
      throw e
    }
  }

  const activeCount = modules.filter(m => m.enabled).length
  const totalCount = modules.length

  return (
    <div className="p-6">
      {loading && (
        <div className="text-center text-gray-500 py-6">
          Cargando módulos activos desde la configuración...
        </div>
      )}

      {fetchError && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
          No se pudo cargar la configuración de módulos: {fetchError}
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          Módulos del Sistema
        </h1>
        <p className="text-gray-600">
          Activa o desactiva módulos según las necesidades de tu negocio
        </p>
        <div className="mt-4 inline-block bg-blue-100 text-blue-800 px-4 py-2 rounded-lg font-semibold">
          {t('settings.modulesActive', { active: activeCount, total: totalCount })}
        </div>
      </div>

      {/* Tabs de Categorías */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex gap-1 overflow-x-auto">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveTab(cat)}
              className={`
                px-4 py-2 font-medium transition-colors whitespace-nowrap
                ${activeTab === cat
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
                }
              `}
            >
              {cat}
              {cat !== 'Todos' && (
                <span className="ml-2 text-xs bg-gray-200 px-2 py-1 rounded-full">
                  {modules.filter(m => m.category === cat && m.enabled).length}/
                  {modules.filter(m => m.category === cat).length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Grid de Módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredModules.map(module => (
          <ModuleCard
            key={module.id}
            module={module}
            disabled={savingModuleId === module.id}
            onToggle={handleToggle}
            onClick={handleClickModule}
          />
        ))}
      </div>

      {filteredModules.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No hay módulos en esta categoría</p>
        </div>
      )}

      {/* Modal de Configuración */}
      {selectedModule && (
        <ModuleConfigForm
          moduleId={selectedModule.id}
          moduleName={selectedModule.name}
          config={selectedModule.config || {}}
          onSave={handleSaveConfig}
          onClose={() => setSelectedModule(null)}
        />
      )}

      {/* Ayuda */}
      <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-semibold text-yellow-800 mb-2">💡 Consejos</h3>
        <ul className="text-sm text-yellow-700 space-y-1 list-disc pl-5">
          <li>Haz clic en cualquier tarjeta para configurar el módulo</li>
          <li>Los módulos desactivados no aparecerán en el menú principal</li>
          <li>{t('settings.moduleDependencies')}</li>
          <li>La configuración se guarda automáticamente</li>
        </ul>
      </div>
    </div>
  )
}
