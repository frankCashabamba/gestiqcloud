/**
 * UserList - Componente simple y directo para usuarios
 * Sin sobreingeniería ni abstracciones innecesarias
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import type { Usuario } from '@api-types/schemas'

export default function UserList() {
  const { t } = useTranslation(['users', 'common'])
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const checkPermission = usePermission()

  // Estado simple y directo
  const [users, setUsers] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Verificar permisos
  if (!checkPermission('users.read')) {
    return <PermissionDenied permission="users.read" />
  }

  // Fetch directo sin abstracciones
  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('/api/v1/tenant/users')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      setUsers(data.items || [])
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido'
      setError(errorMsg)
      toastError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // Cargar datos al montar
  useEffect(() => {
    fetchUsers()
  }, [])

  // Acciones directas
  const handleEdit = (user: Usuario) => {
    nav(`${user.id}`)
  }

  const handleDelete = async (user: Usuario) => {
    if (!confirm(t('confirm_delete_user'))) return

    try {
      const response = await fetch(`/api/v1/tenant/users/${user.id}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      success(t('user_deleted'))
      fetchUsers() // Refrescar lista
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error al eliminar'
      toastError(errorMsg)
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="text-center p-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">{t('loading_users')}</p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="text-center p-8">
        <div className="text-red-600 text-lg mb-4">Error</div>
        <p className="text-red-600 mb-4">{error}</p>
        <button
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          onClick={fetchUsers}
        >
          Reintentar
        </button>
      </div>
    )
  }

  // Empty state
  if (users.length === 0) {
    return (
      <div className="text-center p-8">
        <div className="text-gray-400 text-6xl mb-4">ðª</div>
        <p className="text-gray-500 mb-4">{t('no_users_found')}</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('users')}</h2>
      </div>

      {/* Table simple y directa */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Email')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Nombre')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Estado')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Acciones')}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {user.email}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {user.first_name} {user.last_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    user.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {user.is_active ? t('Activo') : t('Inactivo')}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(user)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      {t('Editar')}
                    </button>
                    <button
                      onClick={() => handleDelete(user)}
                      className="text-red-600 hover:text-red-900"
                    >
                      {t('Eliminar')}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
