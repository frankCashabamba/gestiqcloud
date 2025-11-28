
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
  nombre_encargado: '',
  apellido_encargado: '',
  email: '',
  username: '',
  password: '',
  es_admin_empresa: false,
  activo: true,
  modulos: [],
  roles: [],
}

export default function UsuarioForm() {
  const { id } = useParams()
  const nav = useNavigate()
  // Validación de permisos: solo admins de empresa pueden gestionar usuarios
  const { loading, profile } = useAuth()
  const isAdmin = Boolean((profile as any)?.es_admin_empresa) || Boolean(profile?.roles?.includes('admin'))
  if (loading) return null
  if (!isAdmin) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold text-slate-900">Acceso restringido</h2>
        <p className="mt-2 text-sm text-slate-600">No tienes permisos para gestionar usuarios.</p>
        <button className="gc-button gc-button--ghost mt-4" onClick={() => nav('..')}>Volver</button>
      </div>
    )
  }
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
  }, [])

  useEffect(() => {
    if (!id) return
    setBusy(true)
    let cancelled = false
    ;(async () => {
      try {
        const usuario = await getUsuario(id)
        if (cancelled) return
        setForm({
          nombre_encargado: usuario.nombre_encargado ?? '',
          apellido_encargado: usuario.apellido_encargado ?? '',
          email: usuario.email,
          username: usuario.username ?? '',
          password: '',
          es_admin_empresa: usuario.es_admin_empresa,
          activo: usuario.active,
          modulos: usuario.modulos ?? [],
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
  }, [id])

  const canEditModulos = useMemo(() => !form.es_admin_empresa, [form.es_admin_empresa])

  const handleCheckboxChange = (key: 'modulos' | 'roles', value: number) => {
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
        throw new Error('Email inválido')
      }
      if (!form.nombre_encargado?.trim()) {
        throw new Error('Name is required')
      }
      if (!editMode && !form.password) {
        throw new Error('La contraseña es obligatoria para nuevos usuarios')
      }

      if (editMode && id) {
        const payload: UsuarioUpdatePayload = {
          nombre_encargado: form.nombre_encargado,
          apellido_encargado: form.apellido_encargado,
          email: form.email,
          username: form.username || undefined,
          password: form.password || undefined,
          es_admin_empresa: form.es_admin_empresa,
          activo: form.activo,
          modulos: canEditModulos ? form.modulos : undefined,
          roles: canEditModulos ? form.roles : undefined,
        }
        await updateUsuario(id, payload)
        success('Usuario actualizado')
      } else {
        const payload: UsuarioCreatePayload = {
          ...form,
          modulos: canEditModulos ? form.modulos : [],
          roles: canEditModulos ? form.roles : [],
        }
        await createUsuario(payload)
        success('Usuario creado')
      }
      nav('..')
    } catch (e: any) {
      errorRef.current(getErrorMessage(e))
    }
  }

  const handleUsernameBlur = async (event: React.FocusEvent<HTMLInputElement>) => {
    const value = event.target.value.trim()
    if (!value) return
    try {
      setCheckingUsername(true)
      const available = await checkUsernameAvailability(value)
      if (!available) {
        errorRef.current('Ese nombre de usuario ya esta en uso')
      }
    } catch (e: any) {
      errorRef.current(getErrorMessage(e))
    } finally {
      setCheckingUsername(false)
    }
  }

  return (
    <div className="p-4 max-w-3xl">
      <h3 className="text-xl font-semibold text-slate-900 mb-4">
        {editMode ? 'Editar usuario' : 'Nuevo usuario'}
      </h3>
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">Nombre</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.nombre_encargado ?? ''}
              onChange={(e) => setForm({ ...form, nombre_encargado: e.target.value })}
              required
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">Apellido</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.apellido_encargado ?? ''}
              onChange={(e) => setForm({ ...form, apellido_encargado: e.target.value })}
            />
          </label>
        </div>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-600">Correo electrónico</span>
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
            <span className="font-medium text-slate-600">Nombre de usuario</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.username ?? ''}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              onBlur={handleUsernameBlur}
            />
            {checkingUsername && <span className="text-xs text-slate-400">Verificando…</span>}
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">contraseña {editMode && '(opcional)'}</span>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder={editMode ? 'Dejar en blanco para mantener la actual' : ''}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
          <input
            type="checkbox"
            checked={form.es_admin_empresa}
            onChange={(e) => setForm({ ...form, es_admin_empresa: e.target.checked })}
          />
          Administrador de la empresa (acceso total)
        </label>

        {canEditModulos && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-700">Módulos habilitados</h4>
            <p className="text-xs text-slate-500 mb-2">Selecciona los Módulos a los que tendrá acceso este usuario.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {modules.map((mod) => (
                <label key={mod.id} className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={form.modulos.includes(mod.id)}
                    onChange={() => handleCheckboxChange('modulos', mod.id)}
                  />
                  <span>{mod.name || `Módulo #${mod.id}`}</span>
                </label>
              ))}
              {!modules.length && <p className="text-xs text-slate-400">No hay Módulos contratados.</p>}
            </div>
          </div>
        )}

        {canEditModulos && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-700">Roles</h4>
            <p className="text-xs text-slate-500 mb-2">Puedes asignar uno o varios roles definidos para la empresa.</p>
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
              {!roles.length && <p className="text-xs text-slate-400">No hay roles definidos. Puedes crearlos desde Configuración.</p>}
            </div>
          </div>
        )}

        <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
          <input
            type="checkbox"
            checked={form.activo}
            onChange={(e) => setForm({ ...form, activo: e.target.checked })}
          />
          Usuario activo
        </label>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="gc-button gc-button--primary"
            disabled={busy}
          >
            {editMode ? 'Guardar cambios' : 'Crear usuario'}
          </button>
          <button
            type="button"
            className="gc-button gc-button--ghost"
            onClick={() => nav('..')}
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
