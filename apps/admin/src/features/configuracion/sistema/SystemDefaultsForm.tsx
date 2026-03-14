import React, { useEffect, useState } from 'react'

import {
  listSystemDefaults,
  updateSystemDefault,
  type SystemDefault,
} from '../../../services/configuracion/system-defaults'
import { getErrorMessage, useToast } from '../../../shared/toast'

const CATEGORY_LABELS: Record<string, string> = {
  reports: 'Reportes',
  invoicing: 'Facturación',
  tax: 'Impuestos',
  general: 'General',
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
        rows.forEach((r) => { init[r.key] = r.value_text ?? '' })
        setEdited(init)
      })
      .catch((e) => toastError(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async (key: string) => {
    setSaving(key)
    try {
      const updated = await updateSystemDefault(key, edited[key] ?? '')
      setItems((prev) =>
        prev.map((it) => (it.key === key ? { ...it, value_text: updated.value_text } : it)),
      )
      success(`"${key}" actualizado`)
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setSaving(null)
    }
  }

  // Agrupar por categoría
  const categories = Array.from(new Set(items.map((it) => it.category)))

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-1">Defaults del sistema</h3>
      <p className="text-sm text-gray-500 mb-4">
        Valores globales del sistema que sustituyen a los hardcodeados. Se aplican a todos los
        tenants salvo que tengan configuración propia.
      </p>

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}

      {categories.map((cat) => (
        <section key={cat} className="mb-6">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">
            {CATEGORY_LABELS[cat] ?? cat}
          </h4>
          <div className="bg-white border border-gray-200 rounded divide-y">
            {items
              .filter((it) => it.category === cat)
              .map((it) => (
                <div key={it.key} className="flex items-start gap-4 px-4 py-3">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm text-gray-700">{it.key}</div>
                    {it.description && (
                      <div className="text-xs text-gray-400 mt-0.5">{it.description}</div>
                    )}
                    {it.updated_at && (
                      <div className="text-xs text-gray-300 mt-0.5">
                        Actualizado: {new Date(it.updated_at).toLocaleString('es')}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2" style={{ minWidth: 220 }}>
                    <input
                      type={it.value_type === 'number' ? 'number' : 'text'}
                      step="any"
                      value={edited[it.key] ?? ''}
                      onChange={(e) =>
                        setEdited((prev) => ({ ...prev, [it.key]: e.target.value }))
                      }
                      className="border px-2 py-1 rounded text-sm w-32"
                    />
                    <span className="text-xs text-gray-400 w-12">
                      {it.value_type === 'number' ? 'número' : 'texto'}
                    </span>
                    <button
                      onClick={() => handleSave(it.key)}
                      disabled={saving === it.key}
                      className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                    >
                      {saving === it.key ? '…' : 'Guardar'}
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </section>
      ))}

      {!loading && items.length === 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
          No hay defaults configurados. Reinicia el servidor para que se genere la tabla con los
          valores iniciales.
        </div>
      )}
    </div>
  )
}
