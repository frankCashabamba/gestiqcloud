import React, { useEffect, useState } from 'react'

import { useAuthGuard } from '../hooks/useAuthGuard'
import {
  listUsuarios,
  reenviarReset,
  activarUsuario,
  desactivarUsuario,
  desactivarEmpresa,
  setPasswordDirect,
  type AdminUsuario,
} from '../services/usuarios'
import { useToast, getErrorMessage } from '../shared/toast'

const AVATAR_COLORS = [
  'bg-violet-100 text-violet-700',
  'bg-blue-100 text-blue-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
  'bg-cyan-100 text-cyan-700',
]

function avatarColor(str: string) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

export default function Usuarios() {
  useAuthGuard('superadmin')
  const [items, setItems] = useState<AdminUsuario[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [confirmEmpresaId, setConfirmEmpresaId] = useState<number | string | null>(null)
  const [setPwdUserId, setSetPwdUserId] = useState<number | string | null>(null)
  const [setPwdUser, setSetPwdUser] = useState<AdminUsuario | null>(null)
  const [newPwd, setNewPwd] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const { success, error: toastError } = useToast()

  const load = async () => {
    try {
      setLoading(true)
      const data = await listUsuarios()
      const normalized = (data || []).map((u) => ({
        ...u,
        name: u.name || '',
        email: u.email || '',
        username: u.username || '',
        is_company_admin: u.is_company_admin ?? false,
        active: u.active ?? false,
      }))
      setItems(normalized)
    } catch (e: any) {
      const m = getErrorMessage(e)
      setErrMsg(m)
      toastError(m)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = items.filter((u) => {
    const q = query.toLowerCase()
    return (
      `${u.name || ''}`.toLowerCase().includes(q) ||
      `${u.email || ''}`.toLowerCase().includes(q) ||
      `${u.username || ''}`.toLowerCase().includes(q)
    )
  })

  const activeCount = items.filter((u) => u.active).length

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">

      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usuarios principales</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Administradores de empresa registrados en la plataforma
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-600">
            {items.length} usuarios
          </span>
          <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700">
            {activeCount} activos
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <svg className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          type="text"
          placeholder="Buscar por nombre, usuario o correo…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <svg className="animate-spin" width="16" height="16" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Cargando…
        </div>
      )}
      {errMsg && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <svg width="16" height="16" className="shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-.75-11.25a.75.75 0 011.5 0v4a.75.75 0 01-1.5 0v-4zm.75 7a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          {errMsg}
        </div>
      )}

      {/* Table */}
      {!loading && filtered.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">Usuario</th>
                <th className="hidden px-5 py-3 sm:table-cell">Contacto</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((u) => {
                const initials = (u.name || u.email || '?').charAt(0).toUpperCase()
                const color = avatarColor(u.email || u.name || String(u.id))
                return (
                  <tr key={u.id} className="group transition-colors hover:bg-gray-50/60">
                    {/* Usuario */}
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-semibold ${color}`}>
                          {initials}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-gray-900">
                            {u.username ? `@${u.username}` : <span className="text-gray-400 italic">sin usuario</span>}
                          </p>
                          <p className="truncate text-xs text-gray-500">
                            {u.name || <span className="italic">Sin nombre</span>}
                          </p>
                        </div>
                      </div>
                    </td>
                    {/* Contacto */}
                    <td className="hidden px-5 py-4 sm:table-cell">
                      <span className="text-gray-600">{u.email || '-'}</span>
                    </td>
                    {/* Estado */}
                    <td className="px-5 py-4">
                      {u.active ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
                          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                          <span className="h-1.5 w-1.5 rounded-full bg-gray-400" />
                          Inactivo
                        </span>
                      )}
                    </td>
                    {/* Acciones */}
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap items-center justify-end gap-1.5">
                        <button
                          title="Reenviar correo de reset"
                          onClick={async () => {
                            try { await reenviarReset(u.id); success('Correo de restablecimiento enviado') }
                            catch (e: any) { toastError(getErrorMessage(e)) }
                          }}
                          className="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 shadow-sm transition hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700"
                        >
                          Reenviar correo
                        </button>
                        <button
                          title="Establecer contraseña"
                          onClick={() => { setSetPwdUserId(u.id); setSetPwdUser(u); setNewPwd(''); setShowPwd(false) }}
                          className="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 shadow-sm transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                        >
                          Contraseña
                        </button>
                        {u.active ? (
                          <>
                            <button
                              onClick={async () => {
                                try { await desactivarUsuario(u.id); success('Usuario desactivado'); load() }
                                catch (e: any) { toastError(getErrorMessage(e)) }
                              }}
                              className="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 shadow-sm transition hover:border-amber-300 hover:bg-amber-50 hover:text-amber-700"
                            >
                              Desactivar
                            </button>
                            <button
                              onClick={() => setConfirmEmpresaId(u.id)}
                              className="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 shadow-sm transition hover:border-red-300 hover:bg-red-50 hover:text-red-700"
                            >
                              Eliminar
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={async () => {
                              try { await activarUsuario(u.id); success('Usuario activado'); load() }
                              catch (e: any) { toastError(getErrorMessage(e)) }
                            }}
                            className="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 shadow-sm transition hover:border-green-300 hover:bg-green-50 hover:text-green-700"
                          >
                            Activar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 py-16 text-center">
          <p className="text-sm text-gray-400">No hay usuarios que coincidan con la búsqueda.</p>
        </div>
      )}

      {/* Modal: confirmar acción sobre empresa */}
      {confirmEmpresaId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-amber-100 text-amber-600">
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
              </div>
              <div>
                <h2 className="font-semibold text-gray-900">Acción sobre empresa</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Este usuario es el administrador principal. Puedes asignar otro usuario o desactivar la empresa completa.
                </p>
              </div>
            </div>
            <div className="space-y-2 pt-1">
              <a
                href={`/admin/users/${confirmEmpresaId}/assign-new-admin`}
                className="block rounded-lg bg-blue-600 px-4 py-2.5 text-center text-sm font-medium text-white hover:bg-blue-700"
              >
                Asignar otro administrador
              </a>
              <button
                onClick={async () => {
                  try { await desactivarEmpresa(confirmEmpresaId!); success('Empresa desactivada'); setConfirmEmpresaId(null); load() }
                  catch (e: any) { toastError(getErrorMessage(e)) }
                }}
                className="w-full rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700 hover:bg-red-100"
              >
                Desactivar empresa
              </button>
              <button
                onClick={() => setConfirmEmpresaId(null)}
                className="w-full py-2 text-sm text-gray-500 hover:text-gray-800"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: establecer contraseña */}
      {setPwdUserId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-xl">
            <div>
              <h3 className="font-semibold text-gray-900">Establecer contraseña</h3>
              <p className="mt-0.5 text-sm text-gray-500">Define una contraseña temporal para este usuario.</p>
            </div>
            {setPwdUser && (
              <div className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-semibold ${avatarColor(setPwdUser.email || setPwdUser.name || String(setPwdUser.id))}`}>
                  {(setPwdUser.name || setPwdUser.email || '?').charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">{setPwdUser.name || setPwdUser.email}</p>
                  {setPwdUser.username && <p className="text-xs text-gray-400">@{setPwdUser.username}</p>}
                </div>
              </div>
            )}
            <div className="relative">
              <input
                type={showPwd ? 'text' : 'password'}
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
                placeholder="Nueva contraseña (mín. 8 caracteres)"
                className="w-full rounded-lg border border-gray-200 px-3 py-2.5 pr-10 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <button
                type="button"
                onClick={() => setShowPwd((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPwd ? (
                  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                onClick={() => { setSetPwdUserId(null); setSetPwdUser(null); setNewPwd('') }}
                className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                Cancelar
              </button>
              <button
                onClick={async () => {
                  if ((newPwd || '').length < 8) { toastError('La contraseña debe tener al menos 8 caracteres'); return }
                  try {
                    await setPasswordDirect(setPwdUserId!, newPwd)
                    success('Contraseña actualizada')
                    setSetPwdUserId(null)
                    setSetPwdUser(null)
                    setNewPwd('')
                  } catch (e: any) {
                    toastError(getErrorMessage(e))
                  }
                }}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
