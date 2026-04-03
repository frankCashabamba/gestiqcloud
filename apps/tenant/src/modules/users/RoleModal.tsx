import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createRol,
  updateRol,
  listAvailablePermissions,
  type GlobalPermission,
  type RolCreatePayload,
} from './services'
import type { Rol } from './types'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useSectorPlaceholder } from '../../hooks/useSectorPlaceholders'
import { useCompany } from '../../contexts/CompanyContext'

type Props = {
  rol?: Rol | null
  onClose: () => void
  onSuccess: () => void
}

const normalizePermissionKey = (key: string) => key.trim().toLowerCase().replace(/:/g, '.')

const flattenRolePermissions = (input: unknown): Record<string, boolean> => {
  const result: Record<string, boolean> = {}
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return result
  }

  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [action, allowed] of Object.entries(value as Record<string, unknown>)) {
        if (allowed) {
          result[normalizePermissionKey(`${key}.${action}`)] = true
        }
      }
      continue
    }
    if (value) {
      result[normalizePermissionKey(key)] = true
    }
  }

  return result
}

export default function RolModal({ rol, onClose, onSuccess }: Props) {
  const { t } = useTranslation(['users', 'common'])
  const [nombre, setNombre] = useState('')
  const [description, setDescription] = useState('')
  const [permissions, setPermissions] = useState<Record<string, boolean>>({})
  const [availablePermissions, setAvailablePermissions] = useState<GlobalPermission[]>([])
  const [moduleFilter, setModuleFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const { success, error: toastError } = useToast()
  const { sector } = useCompany()
  const { placeholder: nombrePlaceholder } = useSectorPlaceholder(
    sector?.plantilla || null,
    'nombre',
    'roles'
  )

  useEffect(() => {
    if (rol) {
      setNombre(rol.name)
      setDescription(rol.description || '')
      setPermissions(flattenRolePermissions(rol.permissions || {}))
      return
    }
    setNombre('')
    setDescription('')
    setPermissions({})
  }, [rol])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const perms = await listAvailablePermissions()
        if (!cancelled) {
          setAvailablePermissions(perms)
        }
      } catch (e: any) {
        if (!cancelled) {
          toastError(getErrorMessage(e))
        }
      }
    })()
    return () => { cancelled = true }
  }, [toastError])

  useEffect(() => {
    if (availablePermissions.length === 0) {
      return
    }
    const allowedKeys = new Set(availablePermissions.map((item) => normalizePermissionKey(item.key)))
    setPermissions((prev) =>
      Object.fromEntries(
        Object.entries(prev).filter(([key, allowed]) => allowed && allowedKeys.has(normalizePermissionKey(key)))
      )
    )
  }, [availablePermissions])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!nombre.trim()) {
      toastError(t('users:roleModal.nameRequired'))
      return
    }

    try {
      setLoading(true)
      const payload: RolCreatePayload = {
        name: nombre.trim(),
        description: description.trim() || undefined,
        permissions
      }

      if (rol) {
        await updateRol(rol.id, payload)
        success(t('users:roleModal.updated'))
      } else {
        await createRol(payload)
        success(t('users:roleModal.created'))
      }

      onSuccess()
      onClose()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const togglePermiso = (key: string) => {
    const normalizedKey = normalizePermissionKey(key)
    setPermissions(prev => ({
      ...prev,
      [normalizedKey]: !prev[normalizedKey]
    }))
  }

  // Permisos comunes
  const moduleFromPermission = (p: GlobalPermission) => {
    if (p.module) return p.module.toLowerCase()
    const parts = normalizePermissionKey(p.key || '').split('.')
    return parts.length > 1 ? parts[0] : 'general'
  }

  const moduleCounts = availablePermissions.reduce((acc, p) => {
    const mod = moduleFromPermission(p)
    acc.set(mod, (acc.get(mod) || 0) + 1)
    return acc
  }, new Map<string, number>())

  const modules = Array.from(moduleCounts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name))

  const permisosDisponibles = availablePermissions
    .filter((p) => moduleFilter === 'all' || moduleFromPermission(p) === moduleFilter)
    .map((p) => ({
      key: normalizePermissionKey(p.key),
      label: p.description ? `${p.description} (${p.key})` : p.key,
    }))
    .sort((a, b) => a.label.localeCompare(b.label))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white p-6 shadow-lg"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-slate-900 mb-4">
          {rol ? t('users:roleModal.editRole') : t('users:roleModal.newRole')}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('users:roleModal.roleName')} <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder={nombrePlaceholder || 'E.g.: Cashier, Salesperson, Accountant'}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('users:roleModal.description')}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('users:roleModal.descriptionPlaceholder')}
              rows={3}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              {t('users:roleModal.permissions')}
            </label>
            <div className="flex items-center gap-3 mb-3">
              <label className="text-sm text-slate-600">{t('users:roleModal.module')}</label>
              <select
                value={moduleFilter}
                onChange={(e) => setModuleFilter(e.target.value)}
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
              >
                <option value="all">{t('users:roleModal.all')}</option>
                {modules.map((m) => (
                  <option key={m.name} value={m.name}>{m.name} ({m.count})</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto border border-slate-200 rounded-md p-3">
              {permisosDisponibles.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 p-2 rounded">
                  <input
                    type="checkbox"
                    checked={permissions[key] || false}
                    onChange={() => togglePermiso(key)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900"
              disabled={loading}
            >
              {t('users:roleModal.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('users:roleModal.saving') : (rol ? t('users:roleModal.update') : t('users:roleModal.createRole'))}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
