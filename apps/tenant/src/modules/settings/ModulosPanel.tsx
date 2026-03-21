import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { listAvailableModules } from '../../services/api/settings'
import { getErrorMessage } from '../../shared/toast'

interface Module {
  id: string
  name: string
  icon: string
  description: string
  category: string
  enabled: boolean
}

const CATEGORY_LABELS: Record<string, string> = {
  sales: 'Ventas',
  operations: 'Operaciones',
  finance: 'Finanzas',
  people: 'RRHH',
  analytics: 'Analítica',
  config: 'Configuración',
  core: 'Base',
}

export default function ModulosPanel() {
  const [modules, setModules] = useState<Module[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

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

      setModules(apiModules.map((m: any): Module => ({
        id: m.id || m.code,
        name: m.name,
        icon: m.icon || '📦',
        description: m.description,
        category: CATEGORY_LABELS[m.category] || m.category || 'Otros',
        enabled: Boolean(m.is_enabled ?? m.enabled ?? m.default_enabled),
      })))
    } catch (e: any) {
      setFetchError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadModules() }, [loadModules])

  const activeModules = useMemo(() => modules.filter(m => m.enabled), [modules])
  const byCategory = useMemo(() => {
    const map: Record<string, Module[]> = {}
    activeModules.forEach(m => {
      if (!map[m.category]) map[m.category] = []
      map[m.category].push(m)
    })
    return map
  }, [activeModules])

  return (
    <div className="p-6" style={{ maxWidth: 860 }}>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Módulos activos</h1>
        <p className="text-gray-600 text-sm">
          Estos son los módulos habilitados en tu plan. Para activar o desactivar módulos,
          contacta al equipo de soporte.
        </p>
      </div>

      {loading && (
        <div className="text-center text-gray-400 py-12">Cargando módulos...</div>
      )}

      {fetchError && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
          No se pudo cargar la configuración: {fetchError}
        </div>
      )}

      {!loading && !fetchError && activeModules.length === 0 && (
        <div className="text-center text-gray-400 py-12">
          No hay módulos activos en tu plan actual.
        </div>
      )}

      {!loading && Object.entries(byCategory).map(([cat, mods]) => (
        <div key={cat} className="mb-6">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            {cat}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {mods.map(m => (
              <div
                key={m.id}
                className="border rounded-lg p-4 bg-white flex items-start gap-3"
              >
                <span className="text-2xl leading-none mt-0.5">{m.icon}</span>
                <div>
                  <div className="font-medium text-gray-900 flex items-center gap-2">
                    {m.name}
                    <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                      Activo
                    </span>
                  </div>
                  {m.description && (
                    <p className="text-sm text-gray-500 mt-0.5">{m.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="mt-8 border rounded-lg p-4 bg-slate-50 flex items-start gap-3">
        <span className="text-xl">💬</span>
        <div>
          <p className="font-medium text-slate-800">¿Necesitas cambiar tus módulos?</p>
          <p className="text-sm text-slate-600 mt-1">
            Los módulos de tu cuenta son gestionados por el equipo de GestiqCloud.
            Escríbenos y te ayudamos a configurar el plan ideal para tu negocio.
          </p>
        </div>
      </div>
    </div>
  )
}
