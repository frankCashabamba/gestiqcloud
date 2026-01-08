import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listPermisos, removePermiso, type GlobalPermission } from '../../../services/configuracion/permisos'

function moduleFromPermission(item: GlobalPermission): string {
  if (item.module) return item.module
  const parts = (item.key || '').split('.')
  return parts.length > 1 ? parts[0] : 'general'
}

export default function PermisosList() {
  const [items, setItems] = useState<GlobalPermission[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [moduleFilter, setModuleFilter] = useState('all')
  const nav = useNavigate()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listPermisos())
      } catch (e: any) {
        setError(e?.response?.data?.detail || e?.message || 'No se pudieron cargar los permisos')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const modules = useMemo(() => {
    const set = new Set(items.map((it) => moduleFromPermission(it)))
    return ['all', ...Array.from(set).sort()]
  }, [items])

  const filtered = useMemo(() => {
    if (moduleFilter === 'all') return items
    return items.filter((it) => moduleFromPermission(it) === moduleFilter)
  }, [items, moduleFilter])

  return (
    <div style={{ padding: 16 }}>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xl font-semibold">Permisos globales</h3>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nuevo</button>
      </div>
      <div className="flex items-center gap-3 mb-3">
        <label className="text-sm text-gray-600">Módulo</label>
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="border px-2 py-1 rounded"
        >
          {modules.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando</div>}
      {error && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{error}</div>}
      <table className="min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">Módulo</th>
            <th className="text-left py-2 px-3">Key</th>
            <th className="text-left py-2 px-3">Descripción</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2 px-3">{moduleFromPermission(it)}</td>
              <td className="py-2 px-3">{it.key}</td>
              <td className="py-2 px-3">{it.description || '-'}</td>
              <td className="py-2 px-3">
                <Link to={`${it.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async () => {
                  if (!confirm('Eliminar permiso?')) return
                  await removePermiso(it.id)
                  setItems((prev) => prev.filter(x => x.id !== it.id))
                }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && filtered.length === 0 && (
            <tr><td className="py-3 px-3" colSpan={4}>Sin permisos</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
