
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createUsuario,
  getUsuario,
  updateUsuario,
  listModuloOptions,
  listRolOptions,
  checkUsernameAvailability,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { UsuarioCreatePayload, UsuarioUpdatePayload, ModuloOption, RolOption } from './types'
import { useAuth } from '../../auth/AuthContext'

const emptyForm: UsuarioCreatePayload = {
  first_name: '',
  last_name: '',
  email: '',
  username: '',
  password: '',
  is_company_admin: false,
  active: true,
  modules: [],
  roles: [],
}

export default function UsuarioForm() {
  const { id } = useParams()
  const nav = useNavigate()
  // Validación de permisos: solo admins de empresa pueden gestionar usuarios
  const { loading, profile } = useAuth()
  const isAdmin =
    Boolean((profile as any)?.es_admin_empresa) ||
    Boolean((profile as any)?.is_company_admin) ||
    Boolean(profile?.roles?.includes('admin'))
  const [form, setForm] = useState<UsuarioCreatePayload>(emptyForm)
  const [editMode, setEditMode] = useState(false)
  const [busy, setBusy] = useState(false)
  const [modules, setModules] = useState<ModuloOption[]>([])
  const [roles, setRoles] = useState<RolOption[]>([])
  const [checkingUsername, setCheckingUsername] = useState(false)
  const toast = useToast()
  const success = toast.success
  const errorRef = useRef(toast.error)

  useEffect(() => {
    errorRef.current = toast.error
  }, [toast.error])

  useEffect(() => {
    if (loading || !isAdmin) return
    let cancelled = false
    ;(async () => {
      try {
        const [modOpts, rolOpts] = await Promise.all([listModuloOptions(), listRolOptions()])
        if (!cancelled) {
          setModules(modOpts)
          setRoles(rolOpts)
        }
      } catch (e: any) {
        errorRef.current(getErrorMessage(e))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [loading, isAdmin])

  useEffect(() => {
    if (loading || !isAdmin) return
    if (!id) return
    setBusy(true)
    let cancelled = false
    ;(async () => {
      try {
        const usuario = await getUsuario(id)
        if (cancelled) return
        setForm({
          first_name: usuario.first_name ?? '',
          last_name: usuario.last_name ?? '',
          email: usuario.email,
          username: usuario.username ?? '',
          password: '',
          is_company_admin: usuario.is_company_admin,
          active: usuario.active,
          modules: usuario.modules ?? [],
          roles: usuario.roles ?? [],
        })
        setEditMode(true)
      } catch (e: any) {
        if (!cancelled) {
          errorRef.current(getErrorMessage(e))
        }
      } finally {
        if (!cancelled) {
          setBusy(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, loading, isAdmin])

  const canEditModulos = useMemo(() => !form.is_company_admin, [form.is_company_admin])

  const handleCheckboxChange = (key: 'modules' | 'roles', value: string) => {
    setForm((prev) => {
      const list = new Set(prev[key])
      if (list.has(value)) list.delete(value)
      else list.add(value)
      return { ...prev, [key]: Array.from(list) }
    })
  }

  const onSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    try {
      if (!form.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
        throw new Error('Invalid email')
      }
      if (!form.first_name?.trim()) {
        throw new Error('Name is required')
      }
      if (!editMode && !form.password) {
        throw new Error('Password is required for new users')
      }

      if (editMode && id) {
        const payload: UsuarioUpdatePayload = {
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
          username: form.username || undefined,
          password: form.password || undefined,
          is_company_admin: form.is_company_admin,
          active: form.active,
          modules: canEditModulos ? form.modules : undefined,
          roles: canEditModulos ? form.roles : undefined,
        }
        await updateUsuario(id, payload)
        success('User updated')
      } else {
        const payload: UsuarioCreatePayload = {
          ...form,
          modules: canEditModulos ? form.modules : [],
          roles: canEditModulos ? form.roles : [],
        }
        await createUsuario(payload)
        success('User created')
      }
      nav('..')
    } catch (e: any) {
      errorRef.current(getErrorMessage(e))
    }
  }

  const handleUsernameBlur = async (event: React.FocusEvent<HTMLInputElement>) => {
    if (loading || !isAdmin) return
    const value = event.target.value.trim()
    if (!value) return
    try {
      setCheckingUsername(true)
      const available = await checkUsernameAvailability(value)
      if (!available) {
        errorRef.current('That username is already in use')
      }
    } catch (e: any) {
      errorRef.current(getErrorMessage(e))
    } finally {
      setCheckingUsername(false)
    }
  }

  if (loading) return null
  if (!isAdmin) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold text-slate-900">Access restricted</h2>
        <p className="mt-2 text-sm text-slate-600">You do not have permission to manage users.</p>
        <button className="gc-button gc-button--ghost mt-4" onClick={() => nav('..')}>Back</button>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-3xl">
      <h3 className="text-xl font-semibold text-slate-900 mb-4">
        {editMode ? 'Edit user' : 'New user'}
      </h3>
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">First name</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.first_name ?? ''}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              required
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">Last name</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.last_name ?? ''}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </label>
        </div>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-600">Email</span>
          <input
            type="email"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={form.email ?? ''}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">Username</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.username ?? ''}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              onBlur={handleUsernameBlur}
            />
            {checkingUsername && <span className="text-xs text-slate-400">Checking...</span>}
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">Password {editMode && '(optional)'}</span>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder={editMode ? 'Leave blank to keep current' : ''}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
          <input
            type="checkbox"
            checked={form.is_company_admin}
            onChange={(e) => setForm({ ...form, is_company_admin: e.target.checked })}
          />
          Company administrator (full access)
        </label>

        {canEditModulos && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-700">Enabled modules</h4>
            <p className="text-xs text-slate-500 mb-2">Select the modules this user will have access to.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {modules.map((mod) => (
                <label key={mod.id} className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={form.modules.includes(mod.id)}
                    onChange={() => handleCheckboxChange('modules', mod.id)}
                  />
                  <span>{mod.name || `Módulo #${mod.id}`}</span>
                </label>
              ))}
              {!modules.length && <p className="text-xs text-slate-400">No modules contracted.</p>}
            </div>
          </div>
        )}

        {canEditModulos && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-700">Roles</h4>
            <p className="text-xs text-slate-500 mb-2">You can assign one or more roles defined for the company.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((rol) => (
                <label key={rol.id} className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={form.roles.includes(rol.id)}
                    onChange={() => handleCheckboxChange('roles', rol.id)}
                  />
                  <span>{rol.name}</span>
                </label>
              ))}
              {!roles.length && <p className="text-xs text-slate-400">No roles defined. You can create them from Settings.</p>}
            </div>
          </div>
        )}

        <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
          <input
            type="checkbox"
            checked={form.active}
            onChange={(e) => setForm({ ...form, active: e.target.checked })}
          />
          Active user
        </label>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="gc-button gc-button--primary"
            disabled={busy}
          >
            {editMode ? 'Save changes' : 'Create user'}
          </button>
          <button
            type="button"
            className="gc-button gc-button--ghost"
            onClick={() => nav('..')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
