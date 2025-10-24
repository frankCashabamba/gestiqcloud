/**
 * Roles List - Gestión de roles de empresa
 * Solo visible para es_admin_empresa=true
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listRoles, deleteRol } from './rolesServices'
import type { Rol } from './types'

export default function RolesList() {
  const [roles, setRoles] = useState<Rol[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRoles()
  }, [])

  const loadRoles = async () => {
    try {
      setLoading(true)
      const data = await listRoles()
      setRoles(data)
    } catch (err: any) {
      setError(err.message || 'Error al cargar roles')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar este rol?')) return

    try {
      await deleteRol(id)
      await loadRoles()
    } catch (err: any) {
      alert(err.message || 'Error al eliminar')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Roles de Empresa</h1>
          <p className="mt-1 text-sm text-slate-500">
            Gestiona los roles personalizados de tu empresa
          </p>
        </div>
        <Link
          to="nuevo"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-500"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Rol
        </Link>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      ) : roles.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <p className="mt-4 text-lg font-medium text-slate-900">No hay roles personalizados</p>
          <p className="mt-1 text-sm text-slate-500">
            Crea roles específicos para tu empresa con permisos a medida
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Descripción
                </th>
                <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Permisos
                </th>
                <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Custom
                </th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {roles.map((rol) => (
                <tr key={rol.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <p className="font-semibold text-slate-900">{rol.nombre}</p>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {rol.descripcion || '-'}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className="inline-flex rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                      {Object.keys(rol.permisos || {}).length} permisos
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {rol.creado_por_empresa ? (
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">
                        ✓ Custom
                      </span>
                    ) : (
                      <span className="inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                        Sistema
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`${rol.id}`}
                        className="text-sm text-blue-600 hover:text-blue-500"
                      >
                        Editar
                      </Link>
                      {rol.creado_por_empresa && (
                        <button
                          onClick={() => handleDelete(rol.id)}
                          className="text-sm text-red-600 hover:text-red-500"
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
