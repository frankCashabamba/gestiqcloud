import React, { useEffect, useState } from 'react'

import {
  listSystemDefaults,
  updateSystemDefault,
  type SystemDefault,
} from '../../../services/configuracion/system-defaults'
import { getErrorMessage, useToast } from '../../../shared/toast'

const CATEGORY_LABELS: Record<string, string> = {
  company: 'Empresa',
  reports: 'Reportes',
  invoicing: 'Facturacion',
  tax: 'Impuestos',
  theme: 'Tema',
  general: 'General',
}

const VALUE_TYPE_LABELS: Record<string, string> = {
  number: 'numero',
  text: 'texto',
  color: 'color',
  boolean: 'booleano',
}

export default function SystemDefaultsForm() {
  const [items, setItems] = useState<SystemDefault[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)
  const [edited, setEdited] = useState<Record<string, string>>({})
  const { success, error: toastError } = useToast()

  useEffect(() => {
    setLoading(true)
    listSystemDefaults()
      .then((rows) => {
        setItems(rows)
        const init: Record<string, string> = {}
        rows.forEach((row) => {
          init[row.key] = row.value_text ?? ''
        })
        setEdited(init)
      })
      .catch((error) => toastError(getErrorMessage(error)))
      .finally(() => setLoading(false))
  }, [toastError])

  const handleSave = async (key: string) => {
    setSaving(key)
    try {
      const updated = await updateSystemDefault(key, edited[key] ?? '')
      setItems((prev) =>
        prev.map((item) =>
          item.key === key ? { ...item, value_text: updated.value_text, updated_at: updated.updated_at } : item
        )
      )
      success(`"${key}" actualizado`)
    } catch (error: any) {
      toastError(getErrorMessage(error))
    } finally {
      setSaving(null)
    }
  }

  const categories = Array.from(new Set(items.map((item) => item.category)))

  const renderEditor = (item: SystemDefault) => {
    const value = edited[item.key] ?? ''

    if (item.value_type === 'boolean') {
      const checked = value.toLowerCase() === 'true'
      return (
        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={checked}
            onChange={(event) =>
              setEdited((prev) => ({
                ...prev,
                [item.key]: event.target.checked ? 'true' : 'false',
              }))
            }
          />
          <span>{checked ? 'Activo' : 'Inactivo'}</span>
        </label>
      )
    }

    return (
      <input
        type={item.value_type === 'number' ? 'number' : item.value_type === 'color' ? 'color' : 'text'}
        step={item.value_type === 'number' ? 'any' : undefined}
        value={value}
        onChange={(event) =>
          setEdited((prev) => ({ ...prev, [item.key]: event.target.value }))
        }
        className="border px-2 py-1 rounded text-sm w-40"
      />
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-1">Defaults del sistema</h3>
      <p className="text-sm text-gray-500 mb-4">
        Valores globales del sistema que sustituyen hardcodeos del backend y tema base.
        Se aplican a todos los tenants salvo que tengan configuracion propia.
      </p>

      {loading && <div className="text-sm text-gray-500">Cargando...</div>}

      {categories.map((category) => (
        <section key={category} className="mb-6">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">
            {CATEGORY_LABELS[category] ?? category}
          </h4>
          <div className="bg-white border border-gray-200 rounded divide-y">
            {items
              .filter((item) => item.category === category)
              .map((item) => (
                <div key={item.key} className="flex items-start gap-4 px-4 py-3">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm text-gray-700">{item.key}</div>
                    {item.description && (
                      <div className="text-xs text-gray-400 mt-0.5">{item.description}</div>
                    )}
                    {item.updated_at && (
                      <div className="text-xs text-gray-300 mt-0.5">
                        Actualizado: {new Date(item.updated_at).toLocaleString('es')}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2" style={{ minWidth: 280 }}>
                    {renderEditor(item)}
                    <span className="text-xs text-gray-400 w-16">
                      {VALUE_TYPE_LABELS[item.value_type] ?? item.value_type}
                    </span>
                    <button
                      onClick={() => handleSave(item.key)}
                      disabled={saving === item.key}
                      className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                    >
                      {saving === item.key ? '...' : 'Guardar'}
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </section>
      ))}

      {!loading && items.length === 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
          No hay defaults configurados. Reinicia el servidor para generar la tabla inicial.
        </div>
      )}
    </div>
  )
}
