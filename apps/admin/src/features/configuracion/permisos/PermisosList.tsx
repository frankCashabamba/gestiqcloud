import React, { useEffect, useMemo, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import {
  createPermiso,
  listPermisos,
  removePermiso,
  type GlobalPermission,
} from '../../../services/configuracion/permisos'
import { listModulos } from '../../../services/modulos'

const BASIC_PERMISSION_DEFS = [
  { action: 'read', description: 'Ver' },
  { action: 'create', description: 'Crear' },
  { action: 'update', description: 'Editar' },
  { action: 'delete', description: 'Eliminar' },
] as const

function moduleFromPermission(item: GlobalPermission): string {
  if (item.module) return item.module
  const parts = (item.key || '').split('.')
  return parts.length > 1 ? parts[0] : 'general'
}

function normalizeModuleSlug(raw?: string | null): string | null {
  const value = (raw || '').trim().toLowerCase()
  if (!value) return null

  if (value.includes('/')) {
    const parts = value.split('/').filter(Boolean)
    return parts.at(-1) || null
  }

  return value
}

function getModulePermissionSlug(module: { name?: string | null; url?: string | null }): string | null {
  return normalizeModuleSlug(module.url) || normalizeModuleSlug(module.name)
}

export default function PermisosList() {
  const [items, setItems] = useState<GlobalPermission[]>([])
  const [loading, setLoading] = useState(false)
  const [creatingBasics, setCreatingBasics] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [moduleFilter, setModuleFilter] = useState('all')
  const nav = useNavigate()

  useEffect(() => {
    ;(async () => {
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

  const handleCreateBasicPermissions = async () => {
    try {
      setCreatingBasics(true)
      setError(null)
      setFeedback(null)

      const [modules, permissions] = await Promise.all([listModulos(), listPermisos()])
      const existingKeys = new Set(permissions.map((item) => item.key))
      const moduleSlugs = Array.from(
        new Set(
          modules
            .map((module) => getModulePermissionSlug(module))
            .filter((slug): slug is string => Boolean(slug))
        )
      ).sort()

      const missing = moduleSlugs.flatMap((module) =>
        BASIC_PERMISSION_DEFS
          .map(({ action, description }) => ({
            module,
            key: `${module}.${action}`,
            description: `${description} ${module}`,
          }))
          .filter((permission) => !existingKeys.has(permission.key))
      )

      if (missing.length === 0) {
        setFeedback('No faltaban permisos básicos por crear.')
        return
      }

      const failures: string[] = []

      for (const permission of missing) {
        try {
          await createPermiso(permission)
        } catch (e: any) {
          failures.push(
            `${permission.key}: ${e?.response?.data?.detail || e?.message || 'error desconocido'}`
          )
        }
      }

      setItems(await listPermisos())
      setFeedback(`Se crearon ${missing.length - failures.length} permisos básicos.`)
      if (failures.length > 0) {
        setError(failures.slice(0, 3).join(' | '))
      }
    } finally {
      setCreatingBasics(false)
    }
  }

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
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xl font-semibold">Permisos globales</h3>
        <div className="flex items-center gap-2">
          <button
            className="rounded bg-emerald-600 px-3 py-1 text-white disabled:opacity-60"
            onClick={handleCreateBasicPermissions}
            disabled={creatingBasics}
          >
            {creatingBasics ? 'Creando básicos...' : 'Crear básicos'}
          </button>
          <button className="rounded bg-blue-600 px-3 py-1 text-white" onClick={() => nav('nuevo')}>
            Nuevo
          </button>
        </div>
      </div>
      <div className="mb-3 flex items-center gap-3">
        <label className="text-sm text-gray-600">Módulo</label>
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="rounded border px-2 py-1"
        >
          {modules.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando</div>}
      {error && <div className="mb-3 rounded bg-red-100 px-3 py-2 text-red-700">{error}</div>}
      {feedback && (
        <div className="mb-3 rounded bg-emerald-100 px-3 py-2 text-emerald-700">{feedback}</div>
      )}
      <table className="min-w-full rounded border border-gray-200 bg-white">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left">Módulo</th>
            <th className="px-3 py-2 text-left">Key</th>
            <th className="px-3 py-2 text-left">Descripción</th>
            <th className="px-3 py-2 text-left">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="px-3 py-2">{moduleFromPermission(it)}</td>
              <td className="px-3 py-2">{it.key}</td>
              <td className="px-3 py-2">{it.description || '-'}</td>
              <td className="px-3 py-2">
                <Link to={`${it.id}/editar`} className="mr-3 text-blue-600 hover:underline">
                  Editar
                </Link>
                <button
                  className="text-red-700"
                  onClick={async () => {
                    if (!confirm('Eliminar permiso?')) return
                    await removePermiso(it.id)
                    setItems((prev) => prev.filter((x) => x.id !== it.id))
                  }}
                >
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
          {!loading && filtered.length === 0 && (
            <tr>
              <td className="px-3 py-3" colSpan={4}>
                Sin permisos
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
