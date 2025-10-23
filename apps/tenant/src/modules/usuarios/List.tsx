import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  listUsuarios,
  removeUsuario,
  listModuloOptions,
  listRolOptions,
  setUsuarioPassword,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Usuario, ModuloOption, RolOption } from './types'
import { useAuth } from '../../auth/AuthContext'

function formatNombre(usuario: Usuario): string {
  const parts = [usuario.nombre_encargado, usuario.apellido_encargado].filter(Boolean)
  if (parts.length) return parts.join(' ')
  return usuario.email
}

export default function UsuariosList() {
  const [items, setItems] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [modulos, setModulos] = useState<ModuloOption[]>([])
  const [roles, setRoles] = useState<RolOption[]>([])
  const [setPwdUserId, setSetPwdUserId] = useState<number | string | null>(null)
  const [newPwd, setNewPwd] = useState('')
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const { profile } = useAuth()
  const isAdminEmpresa = Boolean((profile as any)?.es_admin_empresa) || Boolean(profile?.roles?.includes('admin'))

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [usuarios, modOpts, rolOpts] = await Promise.all([
          listUsuarios(),
          listModuloOptions(),
          listRolOptions(),
        ])
        setItems(Array.isArray(usuarios) ? usuarios : [])
        setModulos(Array.isArray(modOpts) ? modOpts : [])
        setRoles(Array.isArray(rolOpts) ? rolOpts : [])
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [toastError])

  const modulosMap = useMemo(() => new Map(modulos.map((m) => [m.id, m])), [modulos])
  const rolesMap = useMemo(() => new Map(roles.map((r) => [r.id, r])), [roles])

  const filtered = useMemo(() => {
    const term = q.toLowerCase()
    if (!term) return items
    return items.filter((u) => {
      const nombre = formatNombre(u).toLowerCase()
      const email = u.email?.toLowerCase() || ''
      const username = u.username?.toLowerCase() || ''
      return nombre.includes(term) || email.includes(term) || username.includes(term)
    })
  }, [items, q])

  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  const handleRemove = async (id: number | string) => {
    if (!confirm('¿Desactivar este usuario?')) return
    try {
      await removeUsuario(id)
      setItems((prev) => prev.filter((u) => u.id !== id))
      success('Usuario desactivado')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Usuarios de la empresa</h2>
          <p className="text-sm text-slate-500">Gestiona accesos, módulos y roles asignados.</p>
        </div>
        {isAdminEmpresa && (
          <button className="gc-button gc-button--primary" onClick={() => nav('nuevo')}>
            Nuevo usuario
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nombre, email o usuario"
          className="w-full max-w-md rounded-xl border border-slate-200 px-4 py-2 text-sm"
        />
      </div>

      {loading && <div className="text-sm text-slate-500">Cargando usuarios…</div>}
      {errMsg && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">{errMsg}</div>}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Email / Usuario</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Módulos</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {view.map((u) => {
              const rolesLabels = u.roles.map((id) => rolesMap.get(id)?.nombre || `#${id}`)
              const modLabels = u.modulos.map((id) => modulosMap.get(id)?.nombre || `#${id}`)
              return (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{formatNombre(u)}</div>
                    {u.es_admin_empresa && (
                      <span className="mt-1 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">Admin</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    <div>{u.email}</div>
                    {u.username && <div className="text-xs text-slate-400">{u.username}</div>}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{rolesLabels.length ? rolesLabels.join(', ') : '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{u.es_admin_empresa ? 'Todos los módulos' : modLabels.join(', ') || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${u.activo ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      {isAdminEmpresa && (
                        <>
                          <Link to={`${u.id}/editar`} className="text-sm font-medium text-blue-600 hover:text-blue-500">
                            Editar
                          </Link>
                          <button
                            className="text-sm font-medium text-slate-600 hover:text-slate-900"
                            onClick={() => { setSetPwdUserId(u.id); setNewPwd('') }}
                          >
                            Establecer contraseña
                          </button>
                          <button
                            className="text-sm font-medium text-rose-600 hover:text-rose-500"
                            onClick={() => handleRemove(u.id)}
                          >
                            Desactivar
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
            {!loading && view.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={6}>
                  No se encontraron usuarios con ese filtro.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />

      {setPwdUserId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-slate-900">Establecer contraseña</h3>
            <p className="text-sm text-slate-600">Define una contraseña temporal para este usuario.</p>
            <input
              type="password"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
              placeholder="Nueva contraseña (mínimo 8)"
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
                    await setUsuarioPassword(setPwdUserId!, newPwd)
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
