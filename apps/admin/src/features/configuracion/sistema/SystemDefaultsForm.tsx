import React, { useEffect, useState } from 'react'

import {
  listSystemDefaults,
  updateSystemDefault,
  type SystemDefault,
} from '../../../services/configuracion/system-defaults'
import { getErrorMessage, useToast } from '../../../shared/toast'

const CATEGORY_LABELS: Record<string, string> = {
  app: 'App',
  company: 'Empresa',
  reports: 'Reportes',
  invoicing: 'Facturación',
  tax: 'Impuestos',
  theme: 'Tema',
  general: 'General',
  modules: 'Módulos',
  numbering: 'Numeración',
  pos: 'Punto de venta',
  sector: 'Sector',
}

function isJsonValue(val: string): boolean {
  const v = val.trim()
  return v.startsWith('{') || v.startsWith('[')
}

function splitKey(key: string): { ns: string; name: string } {
  const dot = key.indexOf('.')
  if (dot === -1) return { ns: '', name: key }
  return { ns: key.slice(0, dot), name: key.slice(dot + 1) }
}

function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
  )
}

export default function SystemDefaultsForm() {
  const [items, setItems] = useState<SystemDefault[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)
  const [savingAll, setSavingAll] = useState(false)
  const [edited, setEdited] = useState<Record<string, string>>({})
  const [original, setOriginal] = useState<Record<string, string>>({})
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const { success, error: toastError } = useToast()

  useEffect(() => {
    setLoading(true)
    listSystemDefaults()
      .then((rows) => {
        setItems(rows)
        const init: Record<string, string> = {}
        rows.forEach((row) => { init[row.key] = row.value_text ?? '' })
        setEdited(init)
        setOriginal(init)
        const firstCat = rows[0]?.category ?? null
        setActiveCategory(firstCat)
      })
      .catch((e) => toastError(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [])

  const isDirty = (key: string) => edited[key] !== original[key]

  const categories = Array.from(new Set(items.map((i) => i.category)))

  const dirtyInCategory = (cat: string) =>
    items.filter((i) => i.category === cat && isDirty(i.key)).length

  const allDirtyKeys = items.filter((i) => isDirty(i.key)).map((i) => i.key)

  const handleSave = async (key: string) => {
    setSaving(key)
    try {
      const updated = await updateSystemDefault(key, edited[key] ?? '')
      setItems((prev) =>
        prev.map((item) =>
          item.key === key
            ? { ...item, value_text: updated.value_text, updated_at: updated.updated_at }
            : item
        )
      )
      setOriginal((prev) => ({ ...prev, [key]: edited[key] ?? '' }))
      success(`"${key}" actualizado`)
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setSaving(null)
    }
  }

  const handleSaveAll = async () => {
    setSavingAll(true)
    let saved = 0
    let failed = 0
    for (const key of allDirtyKeys) {
      try {
        const updated = await updateSystemDefault(key, edited[key] ?? '')
        setItems((prev) =>
          prev.map((item) =>
            item.key === key
              ? { ...item, value_text: updated.value_text, updated_at: updated.updated_at }
              : item
          )
        )
        setOriginal((prev) => ({ ...prev, [key]: edited[key] ?? '' }))
        saved++
      } catch {
        failed++
      }
    }
    setSavingAll(false)
    if (saved > 0) success(`${saved} valor${saved !== 1 ? 'es' : ''} guardado${saved !== 1 ? 's' : ''}`)
    if (failed > 0) toastError(`${failed} no se pudo${failed !== 1 ? 'n' : ''} guardar`)
  }

  const set = (key: string, value: string) =>
    setEdited((prev) => ({ ...prev, [key]: value }))

  const renderEditor = (item: SystemDefault) => {
    const value = edited[item.key] ?? ''

    if (item.value_type === 'boolean') {
      const checked = value.toLowerCase() === 'true'
      return (
        <div className="flex items-center gap-3">
          <button
            type="button"
            role="switch"
            aria-checked={checked}
            onClick={() => set(item.key, checked ? 'false' : 'true')}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
              checked ? 'bg-blue-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                checked ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          <span className="text-sm text-gray-600">{checked ? 'Activado' : 'Desactivado'}</span>
        </div>
      )
    }

    if (item.value_type === 'color') {
      return (
        <div className="flex items-center gap-3">
          <label className="cursor-pointer" title="Abrir selector de color">
            <div
              className="h-9 w-9 rounded-lg border-2 border-white shadow ring-1 ring-gray-200 flex-shrink-0 transition-transform hover:scale-110"
              style={{ backgroundColor: value || '#ffffff' }}
            />
            <input
              type="color"
              value={value || '#ffffff'}
              onChange={(e) => set(item.key, e.target.value)}
              className="sr-only"
            />
          </label>
          <input
            type="text"
            value={value}
            onChange={(e) => set(item.key, e.target.value)}
            className="border border-gray-200 px-2.5 py-1.5 rounded-md text-sm font-mono w-28 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-gray-50"
            placeholder="#000000"
          />
        </div>
      )
    }

    if (isJsonValue(value) || item.value_type === 'json') {
      return (
        <textarea
          value={value}
          onChange={(e) => set(item.key, e.target.value)}
          rows={Math.min(10, Math.max(3, value.split('\n').length + 1))}
          spellCheck={false}
          className="w-full border border-gray-200 px-3 py-2 rounded-md text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-400 bg-gray-50 resize-y"
        />
      )
    }

    return (
      <input
        type={item.value_type === 'number' ? 'number' : 'text'}
        step={item.value_type === 'number' ? 'any' : undefined}
        value={value}
        onChange={(e) => set(item.key, e.target.value)}
        className="w-full border border-gray-200 px-2.5 py-1.5 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-gray-50"
      />
    )
  }

  const activeItems = items.filter((i) => i.category === activeCategory)

  // Special grid layout for theme colors
  const isColorGroup = activeCategory === 'theme' && activeItems.every(
    (i) => i.value_type === 'color' || i.value_type === 'text'
  )
  const colorItems = activeItems.filter((i) => i.value_type === 'color')
  const nonColorItems = activeItems.filter((i) => i.value_type !== 'color')

  if (loading) {
    return (
      <div className="flex h-96 gap-6 p-4">
        <div className="w-44 flex-shrink-0 space-y-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-8 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
        <div className="flex-1 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border border-gray-100 bg-white p-4 space-y-2">
              <div className="h-4 w-48 rounded bg-gray-200 animate-pulse" />
              <div className="h-3 w-72 rounded bg-gray-100 animate-pulse" />
              <div className="h-8 w-full rounded bg-gray-100 animate-pulse mt-3" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          No hay defaults configurados. Reinicia el servidor para generar la tabla inicial.
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full" style={{ padding: 16 }}>
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Defaults del sistema</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Valores globales aplicados a todos los tenants salvo configuración propia.
          </p>
        </div>
        {allDirtyKeys.length > 0 && (
          <button
            onClick={handleSaveAll}
            disabled={savingAll}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60 hover:bg-blue-700 transition-colors flex-shrink-0 ml-4 shadow-sm"
          >
            {savingAll ? <><Spinner /> Guardando…</> : `Guardar ${allDirtyKeys.length} cambio${allDirtyKeys.length !== 1 ? 's' : ''}`}
          </button>
        )}
      </div>

      {/* Body: sidebar + content */}
      <div className="flex gap-5 flex-1 min-h-0">
        {/* Sidebar */}
        <nav className="w-44 flex-shrink-0 space-y-0.5">
          {categories.map((cat) => {
            const dirty = dirtyInCategory(cat)
            const active = cat === activeCategory
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <span>{CATEGORY_LABELS[cat] ?? cat}</span>
                {dirty > 0 && (
                  <span className={`text-xs rounded-full px-1.5 py-0.5 font-medium ${
                    active ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
                  }`}>
                    {dirty}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0 overflow-y-auto space-y-3">
          {/* Color swatches grid for theme colors */}
          {colorItems.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Colores</p>
              <div className="grid grid-cols-3 gap-3">
                {colorItems.map((item) => {
                  const value = edited[item.key] ?? ''
                  const dirty = isDirty(item.key)
                  const { name } = splitKey(item.key)
                  return (
                    <div
                      key={item.key}
                      className={`rounded-xl border p-3 bg-white transition-colors ${
                        dirty ? 'border-amber-300 ring-1 ring-amber-200' : 'border-gray-200'
                      }`}
                    >
                      <label className="cursor-pointer block mb-2" title="Cambiar color">
                        <div
                          className="h-12 rounded-lg border border-black/10 transition-transform hover:scale-105"
                          style={{ backgroundColor: value || '#ffffff' }}
                        />
                        <input
                          type="color"
                          value={value || '#ffffff'}
                          onChange={(e) => set(item.key, e.target.value)}
                          className="sr-only"
                        />
                      </label>
                      <div className="text-xs font-medium text-gray-700 truncate" title={item.key}>{name}</div>
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <input
                          type="text"
                          value={value}
                          onChange={(e) => set(item.key, e.target.value)}
                          className="flex-1 min-w-0 border border-gray-200 px-1.5 py-1 rounded text-xs font-mono bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-400"
                          placeholder="#000000"
                        />
                        <button
                          onClick={() => handleSave(item.key)}
                          disabled={saving === item.key || !dirty}
                          className={`flex-shrink-0 px-2 py-1 rounded text-xs font-medium transition-colors ${
                            dirty
                              ? 'bg-blue-600 text-white hover:bg-blue-700'
                              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          }`}
                        >
                          {saving === item.key ? <Spinner /> : '✓'}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Non-color settings (or all settings if not theme) */}
          {nonColorItems.length > 0 && (
            <div>
              {colorItems.length > 0 && (
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2 mt-4">Otros</p>
              )}
              <div className="space-y-2">
                {nonColorItems.map((item) => {
                  const dirty = isDirty(item.key)
                  const { ns, name } = splitKey(item.key)
                  const isLong = isJsonValue(edited[item.key] ?? '') || item.value_type === 'json'
                  return (
                    <div
                      key={item.key}
                      className={`rounded-xl border bg-white p-4 transition-colors ${
                        dirty ? 'border-amber-300 ring-1 ring-amber-200' : 'border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {ns && (
                              <span className="text-xs text-gray-400 font-mono">{ns}.</span>
                            )}
                            <span className="text-sm font-semibold text-gray-800 font-mono">{name}</span>
                            {dirty && (
                              <span className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">
                                Sin guardar
                              </span>
                            )}
                          </div>
                          {item.description && (
                            <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{item.description}</p>
                          )}
                        </div>
                        {!isLong && (
                          <button
                            onClick={() => handleSave(item.key)}
                            disabled={saving === item.key || !dirty}
                            className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                              dirty
                                ? 'bg-blue-600 text-white hover:bg-blue-700'
                                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            }`}
                          >
                            {saving === item.key ? <Spinner /> : 'Guardar'}
                          </button>
                        )}
                      </div>

                      {renderEditor(item)}

                      {isLong && (
                        <div className="flex justify-end mt-2">
                          <button
                            onClick={() => handleSave(item.key)}
                            disabled={saving === item.key || !dirty}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                              dirty
                                ? 'bg-blue-600 text-white hover:bg-blue-700'
                                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            }`}
                          >
                            {saving === item.key ? <><Spinner /> Guardando…</> : 'Guardar'}
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
