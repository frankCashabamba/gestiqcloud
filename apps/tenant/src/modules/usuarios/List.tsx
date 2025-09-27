
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  listUsuarios,
  removeUsuario,
  listModuloOptions,
  listRolOptions,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Usuario, ModuloOption, RolOption } from './types'

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
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [usuarios, modOpts, rolOpts] = await Promise.all([
          listUsuarios(),
          listModuloOptions(),
          listRolOptions(),
        ])
        setItems(usuarios)
        setModulos(modOpts)
        setRoles(rolOpts)
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
    if (!confirm('�Desactivar este usuario?')) return
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
          <p className="text-sm text-slate-500">Gestiona accesos, m�dulos y roles asignados.</p>
        </div>
        <button className="gc-button gc-button--primary" onClick={() => nav('nuevo')}>
          Nuevo usuario
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nombre, email o usuario"
          className="w-full max-w-md rounded-xl border border-slate-200 px-4 py-2 text-sm"
        />
      </div>

      {loading && <div className="text-sm text-slate-500">Cargando usuarios�</div>}
      {errMsg && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">{errMsg}</div>}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Email / Usuario</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">M�dulos</th>
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
                    {u.es_admin_empresa && <span className="mt-1 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">Admin</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    <div>{u.email}</div>
                    {u.username && <div className="text-xs text-slate-400">{u.username}</div>}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {rolesLabels.length ? rolesLabels.join(', ') : '�'}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {u.es_admin_empresa ? 'Todos los m�dulos' : modLabels.join(', ') || '�'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${u.activo ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      <Link to={`${u.id}/editar`} className="text-sm font-medium text-blue-600 hover:text-blue-500">
                        Editar
                      </Link>
                      <button
                        className="text-sm font-medium text-rose-600 hover:text-rose-500"
                        onClick={() => handleRemove(u.id)}
                      >
                        Desactivar
                      </button>
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
    </div>
  )
}
