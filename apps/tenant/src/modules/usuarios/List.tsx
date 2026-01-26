import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  listUsuarios,
  removeUsuario,
  listModuloOptions,
  listRolOptions,
  setUsuarioPassword,
  listRoles,
  deleteRol,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Usuario, ModuloOption, RolOption, Rol } from './types'
import { useAuth } from '../../auth/AuthContext'
import RolModal from './RoleModal'

function formatNombre(usuario: Usuario): string {
  const parts = [usuario.first_name, usuario.last_name].filter(Boolean)
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
  const [setPwdUserId, setSetPwdUserId] = useState<string | null>(null)
  const [newPwd, setNewPwd] = useState('')
  const [showRolesModal, setShowRolesModal] = useState(false)
  const [rolesCompletos, setRolesCompletos] = useState<Rol[]>([])
  const [selectedRol, setSelectedRol] = useState<Rol | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const { profile, loading: authLoading, token } = useAuth()
  const isAdminEmpresa =
    Boolean((profile as any)?.es_admin_empresa) ||
    Boolean((profile as any)?.is_company_admin) ||
    Boolean(profile?.roles?.includes('admin'))

  useEffect(() => {
    if (authLoading || !token) return
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const [usuarios, modOpts, rolOpts] = await Promise.all([
          listUsuarios(),
          listModuloOptions(),
          listRolOptions(),
        ])
        if (cancelled) return
        setItems(usuarios)
        setModulos(modOpts)
        setRoles(rolOpts)
      } catch (e: any) {
        if (cancelled) return
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [authLoading, token])

  const modulosMap = useMemo(() => new Map(modulos.map((m) => [m.id, m])), [modulos])
  const rolesMap = useMemo(() => new Map(roles.map((r) => [r.id, r])), [roles])

  const filtered = useMemo(() => {
    // Filtrar usuario actual por username (no mostrarlo en la lista)
    const currentUsername = profile?.username
    const withoutCurrent = currentUsername ? items.filter((u) => u.username !== currentUsername) : items
    const term = q.toLowerCase()
    if (!term) return withoutCurrent
    return withoutCurrent.filter((u) => {
      const nombre = formatNombre(u).toLowerCase()
      const email = u.email?.toLowerCase() || ''
      const username = u.username?.toLowerCase() || ''
      return nombre.includes(term) || email.includes(term) || username.includes(term)
    })
  }, [items, q, profile?.username])

  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  const handleRemove = async (id: string) => {
    if (!confirm('Deactivate this user?')) return
    try {
      await removeUsuario(id)
      setItems((prev) => prev.filter((u) => u.id !== id))
      success('User deactivated')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const loadRoles = async () => {
    if (authLoading || !token) {
      toastError('Not authenticated. Please sign in again.')
      return
    }
    try {
      const data = await listRoles()
      setRolesCompletos(data)
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const handleDeleteRol = async (id: string) => {
    if (!confirm('Delete this role?')) return
    try {
      await deleteRol(id)
      setRolesCompletos(prev => prev.filter(r => r.id !== id))
      success('Role deleted')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Company Users</h2>
          <p className="text-sm text-slate-500">Manage access, modules, and assigned roles.</p>
        </div>
        {isAdminEmpresa && (
          <div className="flex gap-2">
            <button
              className="rounded-md border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50"
              onClick={() => {
                loadRoles()
                setShowRolesModal(true)
              }}
            >
              Manage Roles
            </button>
            <button className="gc-button gc-button--primary" onClick={() => nav('nuevo')}>
              New user
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, email or username"
          className="w-full max-w-md rounded-xl border border-slate-200 px-4 py-2 text-sm"
        />
      </div>

      {loading && <div className="text-sm text-slate-500">Loading users...</div>}
      {errMsg && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">{errMsg}</div>}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email / Username</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Modules</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {view.map((u) => {
              const rolesLabels = (Array.isArray(u.roles) ? u.roles : []).map((id) => rolesMap.get(id)?.name || `#${id}`)
              const modLabels = (Array.isArray(u.modules) ? u.modules : []).map((id) => modulosMap.get(id)?.name || `#${id}`)
              return (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{formatNombre(u)}</div>
                    {u.is_company_admin && (
                      <span className="mt-1 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">Admin</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    <div>{u.email}</div>
                    {u.username && <div className="text-xs text-slate-400">{u.username}</div>}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{rolesLabels.length ? rolesLabels.join(', ') : '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{u.is_company_admin ? 'All modules' : modLabels.join(', ') || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${u.active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                      {u.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      {isAdminEmpresa && (
                        <>
                          <Link to={`${u.id}/editar`} className="text-sm font-medium text-blue-600 hover:text-blue-500">
                            Edit
                          </Link>
                          <button
                            className="text-sm font-medium text-slate-600 hover:text-slate-900"
                            onClick={() => { setSetPwdUserId(u.id); setNewPwd('') }}
                          >
                            Set password
                          </button>
                          <button
                            className="text-sm font-medium text-rose-600 hover:text-rose-500"
                            onClick={() => handleRemove(u.id)}
                          >
                            Deactivate
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
                  No users found matching that filter.
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
            <h3 className="text-lg font-semibold text-slate-900">Set password</h3>
            <p className="text-sm text-slate-600">Define a temporary password for this user.</p>
            <input
              type="password"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
              placeholder="New password (min 8 chars)"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            <div className="flex items-center justify-end gap-2 pt-2">
              <button onClick={() => { setSetPwdUserId(null); setNewPwd('') }} className="text-sm text-slate-600 hover:text-slate-900">
                Cancel
              </button>
              <button
                onClick={async () => {
                  if ((newPwd || '').length < 8) { toastError('Password must be at least 8 characters'); return }
                  try {
                    await setUsuarioPassword(setPwdUserId!, newPwd)
                    success('Password updated')
                    setSetPwdUserId(null)
                    setNewPwd('')
                  } catch (e: any) {
                    toastError(getErrorMessage(e))
                  }
                }}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Gestión de Roles */}
      {showRolesModal && !selectedRol && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowRolesModal(false)}>
          <div
            className="w-full max-w-3xl max-h-[80vh] overflow-y-auto rounded-xl bg-white p-6 shadow-lg"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-slate-900">Role Management</h2>
              <button
                className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
                onClick={() => setSelectedRol({} as Rol)}
              >
                + Create Role
              </button>
            </div>

            <div className="space-y-3">
              {rolesCompletos.length === 0 && (
                <p className="text-center text-sm text-slate-500 py-8">
                  No roles created. Create the first role for your company.
                </p>
              )}
              {rolesCompletos.map(rol => (
                <div key={rol.id} className="border border-slate-200 rounded-lg p-4 hover:bg-slate-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-slate-900">{rol.name}</h3>
                      {rol.description && (
                      <p className="text-sm text-slate-600 mt-1">{rol.description}</p>
                      )}
                      <div className="flex flex-wrap gap-2 mt-2">
                        {Object.entries(rol.permissions || {})
                          .filter(([_, enabled]) => enabled)
                          .map(([key]) => (
                            <span
                              key={key}
                              className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700"
                            >
                              {key.replace(/_/g, ' ')}
                            </span>
                          ))
                        }
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4">
                      <button
                        className="text-sm text-blue-600 hover:text-blue-500"
                        onClick={() => setSelectedRol(rol)}
                      >
                        Edit
                      </button>
                      <button
                        className="text-sm text-rose-600 hover:text-rose-500"
                        onClick={() => handleDeleteRol(rol.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-4 mt-4 border-t">
              <button
                className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900"
                onClick={() => setShowRolesModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Crear/Editar Rol */}
      {selectedRol && (
        <RolModal
          rol={selectedRol.id ? selectedRol : null}
          onClose={() => setSelectedRol(null)}
          onSuccess={() => {
            setSelectedRol(null)
            loadRoles()
          }}
        />
      )}
    </div>
  )
}
