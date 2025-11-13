import React, { useEffect, useMemo, useState } from 'react'
import { suggestMapping, createColumnMapping, type ImportMapping } from '../services/importsApi'
import { useAuth } from '../../../auth/AuthContext'

type Props = {
  file: File | null
  open: boolean
  onClose: () => void
  onSaved: (mapping: ImportMapping) => void
}

const CANONICAL_FIELDS = [
  'sku','name','price','stock','unit','category','image_url','packs','units_per_pack','pack_price'
]

export default function MappingSuggestModal({ file, open, onClose, onSaved }: Props) {
  const { token } = useAuth() as { token: string | null }
  const [headers, setHeaders] = useState<string[]>([])
  const [mapping, setMapping] = useState<Record<string,string>>({})
  const [transforms, setTransforms] = useState<Record<string, any>>({})
  const [defaults, setDefaults] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !file) return
    let cancelled = false
    ;(async () => {
      try {
        setError(null)
        const sug = await suggestMapping(file, token || undefined)
        if (!cancelled) {
          setHeaders(sug.headers || [])
          setMapping(sug.mapping || {})
          setTransforms(sug.transforms || {})
          setDefaults(sug.defaults || {})
        }
      } catch (e:any) {
        if (!cancelled) setError(e?.message || 'No se pudo sugerir el mapping')
      }
    })()
    return () => { cancelled = true }
  }, [open, file, token])

  if (!open) return null

  const save = async () => {
    if (!file) return
    setSaving(true)
    try {
      const base = (file.name || 'mapping').replace(/\.[^.]+$/, '')
      const saved = await createColumnMapping({ name: `auto_${base}`, mapping, description: 'auto-suggest', file_pattern: base }, token || undefined)
      onSaved(saved)
      onClose()
    } catch (e:any) {
      setError(e?.message || 'No se pudo guardar el mapping')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-[90%] max-w-3xl rounded-lg bg-white p-4 shadow-lg">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">Sugerencia de mapeo</h3>
          <button className="text-slate-600 hover:text-slate-900" onClick={onClose}>✕</button>
        </div>
        {error && (
          <div className="mb-3 rounded border border-rose-200 bg-rose-50 p-2 text-sm text-rose-700">{error}</div>
        )}
        <div className="max-h-[50vh] overflow-auto rounded border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-2 py-1 text-left">Columna Excel</th>
                <th className="px-2 py-1 text-left">Campo destino</th>
              </tr>
            </thead>
            <tbody>
              {headers.map((h) => (
                <tr key={h} className="border-t border-slate-100">
                  <td className="px-2 py-1 text-slate-800">{h}</td>
                  <td className="px-2 py-1">
                    <select
                      value={mapping[h] || ''}
                      onChange={(e) => setMapping({ ...mapping, [h]: e.target.value })}
                      className="w-full rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                    >
                      <option value="">(ignorar)</option>
                      {CANONICAL_FIELDS.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-end gap-2">
          <button className="rounded border border-slate-300 px-3 py-1.5 text-sm" onClick={onClose}>Cancelar</button>
          <button
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
            onClick={save}
            disabled={saving}
          >{saving ? 'Guardando...' : 'Guardar mapping y usar'}</button>
        </div>
      </div>
    </div>
  )
}

