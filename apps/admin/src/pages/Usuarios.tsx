import React, { useEffect, useState } from 'react'
import { useAuthGuard } from '../hooks/useAuthGuard'
import { useToast, getErrorMessage } from '../shared/toast'
import {
  listUsuarios,
  reenviarReset,
  activarUsuario,
  desactivarUsuario,
  desactivarEmpresa,
  setPasswordDirect,
  type AdminUsuario,
} from '../services/usuarios'

export default function Usuarios() {
  // Solo superadmin puede ver/editar usuarios principales
  useAuthGuard('superadmin')
  const [items, setItems] = useState<AdminUsuario[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [confirmEmpresaId, setConfirmEmpresaId] = useState<number | string | null>(null)
  const [setPwdUserId, setSetPwdUserId] = useState<number | string | null>(null)
  const [newPwd, setNewPwd] = useState('')
  const { success, error: toastError } = useToast()

  const load = async () => {
    try {
      setLoading(true)
      const data = await listUsuarios()
      const filtrados = (data || []).filter((u: any) => u.es_admin === true || u.es_admin_empresa === true)
      setItems(filtrados)
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
    const name = `${u.nombre || ''}`.toLowerCase()
    const email = `${u.email || ''}`.toLowerCase()
    const q = query.toLowerCase()
    return name.includes(q) || email.includes(q)
  })

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-3xl font-bold text-gray-800">        
          Usuarios Principales
        </h1>
      </div>

      <input
        type="text"
        placeholder="Buscar nombre o correo..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
      />

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="mb-3 rounded bg-red-100 px-3 py-2 text-red-700">{errMsg}</div>}

      {filtered.length > 0 ? (
        <ul className="space-y-4">
          {filtered.map((u) => (
            <li
              key={u.id}
              className="flex flex-col items-start justify-between gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center"
            >
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-slate-100 font-bold text-slate-600">
                  {(u.nombre || u.email || '?').charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{u.nombre}</p>
                  <p className="text-sm text-gray-500">{u.email || '-'}</p>
                  <span
                    className={`inline-block rounded px-2 py-0.5 text-[11px] ${
                      u.activo ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {u.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
              </div>
              <div className="mt-1 flex flex-wrap gap-2 sm:mt-0">
                <button
                  onClick={async () => {
                    try { await reenviarReset(u.id); success('Correo de restablecimiento enviado') } catch (e: any) { toastError(getErrorMessage(e)) }
                  }}
                  className="rounded-md bg-purple-600 px-3 py-1.5 text-xs text-white hover:bg-purple-700"
                >
                  Reenviar correo
                </button>
                <button
                  onClick={() => { setSetPwdUserId(u.id); setNewPwd('') }}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700"
                >
                  Establecer contraseña
                </button>
                {u.activo ? (
                  <>
                    <button
                      onClick={async () => {
                        try { await desactivarUsuario(u.id); success('Usuario desactivado'); load() } catch (e: any) { toastError(getErrorMessage(e)) }
                      }}
                      className="rounded-md bg-red-500 px-3 py-1.5 text-xs text-white hover:bg-red-600"
                    >
                      Desactivar
                    </button>
                    <button
                      onClick={() => setConfirmEmpresaId(u.id)}
                      className="rounded-md bg-gray-500 px-3 py-1.5 text-xs text-white hover:bg-gray-600"
                    >
                      Eliminar
                    </button>
                  </>
                ) : (
                  <button
                    onClick={async () => {
                      try { await activarUsuario(u.id); success('Usuario activado'); load() } catch (e: any) { toastError(getErrorMessage(e)) }
                    }}
                    className="rounded-md bg-green-600 px-3 py-1.5 text-xs text-white hover:bg-green-700"
                  >
                    Activar
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        !loading && <p className="mt-4 text-sm text-gray-500">No hay usuarios principales.</p>
      )}

      {confirmEmpresaId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md space-y-4 rounded-xl bg-white p-6 shadow-lg">
            <h2 className="text-lg font-bold text-gray-800">¿Qué deseas hacer con la empresa?</h2>
            <p className="text-sm text-gray-600">
              Este usuario es el administrador principal. Puedes asignar otro usuario o desactivar la empresa completa.
            </p>
            <div className="space-y-3">
              <a
                href={`/admin/usuarios/${confirmEmpresaId}/asignar-nuevo-admin`}
                className="block rounded-md bg-blue-600 px-4 py-2 text-center text-white hover:bg-blue-700"
              >
                Asignar otro administrador
              </a>
              <button
                onClick={async () => {
                  try { await desactivarEmpresa(confirmEmpresaId!); success('Empresa desactivada'); setConfirmEmpresaId(null); load() } catch (e: any) { toastError(getErrorMessage(e)) }
                }}
                className="w-full rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700"
              >
                Desactivar empresa
              </button>
              <button onClick={() => setConfirmEmpresaId(null)} className="w-full text-sm text-gray-600 hover:text-gray-900">
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {setPwdUserId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-slate-900">Establecer contraseña</h3>
            <p className="text-sm text-slate-600">Define una contraseña temporal para este usuario. Podrá cambiarla después.</p>
            <input
              type="password"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
              placeholder="Nueva contraseña (min 8)"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            <div className="flex items-center justify-end gap-2 pt-2">
              <button onClick={() => { setSetPwdUserId(null); setNewPwd('') }} className="text-sm text-slate-600 hover:text-slate-900">
                Cancelar
              </button>
              <button
                onClick={async () => {
                  if ((newPwd || '').length < 8) { toastError('La contraseña debe tener al menos 8 caracteres'); return }
                  try {
                    await setPasswordDirect(setPwdUserId!, newPwd)
                    success('Contraseña actualizada')
                    setSetPwdUserId(null)
                    setNewPwd('')
                  } catch (e: any) {
                    toastError(getErrorMessage(e))
                  }
                }}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
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

