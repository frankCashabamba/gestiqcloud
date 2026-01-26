import React, { useState, useEffect } from 'react'
import { useToast } from '../../shared/toast'
import { getUIConfig, UIConfig } from './services'

export default function TemplateConfigViewer() {
  const { error: showError } = useToast()
  const [loading, setLoading] = useState(true)
  const [config, setConfig] = useState<UIConfig | null>(null)
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const data = await getUIConfig()
      setConfig(data)
    } catch {
      showError('Error loading template configuration')
    } finally {
      setLoading(false)
    }
  }

  const toggleKey = (key: string) => {
    const newSet = new Set(expandedKeys)
    if (newSet.has(key)) {
      newSet.delete(key)
    } else {
      newSet.add(key)
    }
    setExpandedKeys(newSet)
  }

  if (loading) return <div className="p-6">Loading...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Configuración de Templates</h1>
        <button
          onClick={loadConfig}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Actualizar
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">UI Config Actual</h2>
        <div className="space-y-2">
          {config ? (
            <JSONViewer data={config} expandedKeys={expandedKeys} onToggle={toggleKey} />
          ) : (
            <p className="text-gray-500">No hay configuración</p>
          )}
        </div>
      </div>

      <div className="text-xs text-gray-500">
        <p>Tamaño: {config ? new Blob([JSON.stringify(config)]).size : 0} bytes</p>
        <p>Campos: {config ? countFields(config) : 0}</p>
      </div>
    </div>
  )
}

function countFields(obj: any): number {
  let count = 0
  const visit = (o: any) => {
    if (typeof o === 'object' && o !== null) {
      if (Array.isArray(o)) {
        o.forEach(visit)
      } else {
        count += Object.keys(o).length
        Object.values(o).forEach(visit)
      }
    }
  }
  visit(obj)
  return count
}

function JSONViewer({
  data,
  expandedKeys,
  onToggle,
  path = '',
}: {
  data: any
  expandedKeys: Set<string>
  onToggle: (key: string) => void
  path?: string
}) {
  if (typeof data !== 'object' || data === null) {
    return <span className="text-gray-700">{String(data)}</span>
  }

  if (Array.isArray(data)) {
    return (
      <div className="ml-4">
        <span className="text-gray-500">[{data.length}]</span>
      </div>
    )
  }

  return (
    <div className="space-y-1 ml-4">
      {Object.entries(data).map(([key, value]) => {
        const fullKey = `${path}.${key}`
        const isExpanded = expandedKeys.has(fullKey)
        const hasChildren = typeof value === 'object' && value !== null && !Array.isArray(value) && Object.keys(value).length > 0

        return (
          <div key={key} className="text-sm">
            <div
              className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded"
              onClick={() => hasChildren && onToggle(fullKey)}
            >
              {hasChildren && (
                <span className="w-4 text-center">
                  {isExpanded ? '▼' : '▶'}
                </span>
              )}
              {!hasChildren && <span className="w-4" />}
              <span className="font-mono text-blue-600">{key}:</span>
              {!hasChildren && (
                <span className="text-gray-600">
                  {typeof value === 'string' ? `"${value}"` : String(value)}
                </span>
              )}
            </div>
            {hasChildren && isExpanded && (
              <JSONViewer data={value} expandedKeys={expandedKeys} onToggle={onToggle} path={fullKey} />
            )}
          </div>
        )
      })}
    </div>
  )
}
