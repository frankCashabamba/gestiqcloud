// src/pages/TenantUsuarios.tsx

import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Container } from './Container'
import {
  listTenantUsers,
  createTenantUser,
  updateTenantUser,
  resetUserPassword,
  toggleUserActive,
  deleteUser,
  getUserActivity,
  TenantUser,
  CreateUserPayload,
  UpdateUserPayload,
  UserActivity,
} from '../services/tenant-users'
import { getEmpresa } from '../services/empresa'
import { useToast } from '../shared/toast'

const ROLES_DISPONIBLES = [
  { value: 'owner', label: 'Owner (Admin Total)' },
  { value: 'manager', label: 'Manager (Gestión)' },
  { value: 'cajero', label: 'Cajero/Operario (POS)' },
  { value: 'contable', label: 'Contable (Facturación)' },
  { value: 'vendedor', label: 'Vendedor (Ventas)' },
  { value: 'almacen', label: 'Almacén (Stock)' },
]

export const TenantUsuarios: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [empresa, setEmpresa] = useState<any>(null)
  const [usuarios, setUsuarios] = useState<TenantUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filtroActivo, setFiltroActivo] = useState<'all' | 'activo' | 'inactivo'>('all')

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showActivityModal, setShowActivityModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<TenantUser | null>(null)
  const [userActivity, setUserActivity] = useState<UserActivity[]>([])

  // Form state
  const [formData, setFormData] = useState<CreateUserPayload>({
    email: '',
    name: '',
    apellidos: '',
    password: '',
    roles: [],
  })

  const [editFormData, setEditFormData] = useState<UpdateUserPayload>({
    name: '',
    apellidos: '',
    roles: [],
    active: true,
  })

  // Cargar empresa y usuarios
  useEffect(() => {
    if (!id) return
    loadData()
  }, [id])

  const loadData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [empresaData, usersData] = await Promise.all([
        getEmpresa(id),
        listTenantUsers(id),
      ])
      setEmpresa(empresaData)
      setUsuarios(usersData.users || usersData || [])
    } catch (err: any) {
      showToast('Error al cargar datos', 'error')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Filtrado
  const usuariosFiltrados = usuarios.filter((u) => {
    const matchSearch =
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.name.toLowerCase().includes(search.toLowerCase())
    const matchActivo =
      filtroActivo === 'all' ||
      (filtroActivo === 'activo' && u.active) ||
      (filtroActivo === 'inactivo' && !u.active)
    return matchSearch && matchActivo
  })

  // Crear usuario
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return

    // Validaciones
    if (!formData.email || !formData.name || !formData.password) {
      showToast('Email, nombre y password son obligatorios', 'error')
      return
    }
    if (formData.roles.length === 0) {
      showToast('Debes asignar al menos un rol', 'error')
      return
    }

    try {
      const result = await createTenantUser(id, formData)
      showToast('Usuario creado exitosamente. Se envió email con credenciales.', 'success')
      setShowCreateModal(false)
      resetFormData()
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error al crear usuario', 'error')
      console.error(err)
    }
  }

  // Actualizar usuario
  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !selectedUser) return

    if (!editFormData.roles || editFormData.roles.length === 0) {
      showToast('Debes asignar al menos un rol', 'error')
      return
    }

    try {
      await updateTenantUser(id, selectedUser.id, editFormData)
      showToast('Usuario actualizado exitosamente', 'success')
      setShowEditModal(false)
      setSelectedUser(null)
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error al actualizar usuario', 'error')
      console.error(err)
    }
  }

  // Resetear password
  const handleResetPassword = async (user: TenantUser) => {
    if (!id) return
    if (!confirm(`¿Resetear password de ${user.email}? Se enviará nueva contraseña por email.`)) {
      return
    }

    try {
      await resetUserPassword(id, user.id)
      showToast('Password reseteado. Nuevo password enviado por email.', 'success')
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error al resetear password', 'error')
      console.error(err)
    }
  }

  // Toggle activo
  const handleToggleActive = async (user: TenantUser) => {
    if (!id) return
    const action = user.active ? 'desactivar' : 'activar'
    if (!confirm(`¿Confirmas ${action} al usuario ${user.email}?`)) {
      return
    }

    try {
      await toggleUserActive(id, user.id, !user.active)
      showToast(`Usuario ${action}do exitosamente`, 'success')
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || `Error al ${action} usuario`, 'error')
      console.error(err)
    }
  }

  // Eliminar usuario
  const handleDeleteUser = async (user: TenantUser) => {
    if (!id) return
    if (!confirm(`¿ELIMINAR usuario ${user.email}? Esta acción NO se puede deshacer.`)) {
      return
    }

    try {
      await deleteUser(id, user.id)
      showToast('Usuario eliminado exitosamente', 'success')
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error al eliminar usuario', 'error')
      console.error(err)
    }
  }

  // Ver actividad
  const handleViewActivity = async (user: TenantUser) => {
    try {
      const activity = await getUserActivity(user.id)
      setUserActivity(activity.activity || activity || [])
      setSelectedUser(user)
      setShowActivityModal(true)
    } catch (err: any) {
      showToast('Error al cargar actividad', 'error')
      console.error(err)
    }
  }

  // Abrir modal de edición
  const handleOpenEditModal = (user: TenantUser) => {
    setSelectedUser(user)
    setEditFormData({
      name: user.name,
      apellidos: user.apellidos || '',
      roles: user.roles,
      active: user.active,
    })
    setShowEditModal(true)
  }

  // Reset form
  const resetFormData = () => {
    setFormData({
      email: '',
      name: '',
      apellidos: '',
      password: '',
      roles: [],
    })
  }

  // Manejar checkbox roles
  const toggleRole = (role: string, isCreate: boolean = true) => {
    if (isCreate) {
      setFormData((prev) => ({
        ...prev,
        roles: prev.roles.includes(role)
          ? prev.roles.filter((r) => r !== role)
          : [...prev.roles, role],
      }))
    } else {
      setEditFormData((prev) => ({
        ...prev,
        roles: (prev.roles || []).includes(role)
          ? (prev.roles || []).filter((r) => r !== role)
          : [...(prev.roles || []), role],
      }))
    }
  }

  return (
    <Container className="py-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-600 mb-4">
        <Link to="/admin" className="hover:text-blue-600">Admin</Link>
        {' > '}
        <Link to="/admin/empresas" className="hover:text-blue-600">Empresas</Link>
        {' > '}
        {empresa && <span className="font-medium">{empresa.name}</span>}
        {' > '}
        <span className="font-medium">Usuarios</span>
      </nav>

      {/* Header */}
      <div className="admin-header">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usuarios del Tenant</h1>
          {empresa && <p className="text-gray-600 text-sm mt-1">{empresa.name} (ID: {id})</p>}
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary"
        >
          ➕ Nuevo Usuario
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-4 mb-6">
        <input
          type="search"
          placeholder="Buscar por email o nombre..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input"
        />
        <select
          value={filtroActivo}
          onChange={(e) => setFiltroActivo(e.target.value as any)}
          className="input"
        >
          <option value="all">Todos</option>
          <option value="activo">Activos</option>
          <option value="inactivo">Inactivos</option>
        </select>
      </div>

      {/* Lista de usuarios */}
      {loading ? (
        <p className="text-gray-500">Cargando usuarios...</p>
      ) : usuariosFiltrados.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No hay usuarios para mostrar</p>
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg shadow">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Roles
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Última Conexión
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {usuariosFiltrados.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {user.email}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {user.name} {user.apellidos}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <span
                          key={role}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800"
                        >
                          {role}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {user.active ? (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        Activo
                      </span>
                    ) : (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                        Inactivo
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {user.ultima_conexion
                      ? new Date(user.ultima_conexion).toLocaleString()
                      : 'Nunca'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleOpenEditModal(user)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Editar"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleResetPassword(user)}
                        className="text-yellow-600 hover:text-yellow-900"
                        title="Resetear Password"
                      >
                        🔑
                      </button>
                      <button
                        onClick={() => handleToggleActive(user)}
                        className={user.active ? 'text-orange-600 hover:text-orange-900' : 'text-green-600 hover:text-green-900'}
                        title={user.active ? 'Desactivar' : 'Activar'}
                      >
                        {user.active ? '🚫' : '✅'}
                      </button>
                      <button
                        onClick={() => handleViewActivity(user)}
                        className="text-purple-600 hover:text-purple-900"
                        title="Ver Actividad"
                      >
                        📊
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user)}
                        className="text-red-600 hover:text-red-900"
                        title="Eliminar"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Crear Usuario */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Crear Nuevo Usuario</h2>
            <form onSubmit={handleCreateUser}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Apellidos
                  </label>
                  <input
                    type="text"
                    value={formData.apellidos}
                    onChange={(e) => setFormData({ ...formData, apellidos: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  <p className="text-xs text-gray-500 mt-1">Mín. 8 caracteres</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Roles *
                  </label>
                  <div className="space-y-2">
                    {ROLES_DISPONIBLES.map((rol) => (
                      <label key={rol.value} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={formData.roles.includes(rol.value)}
                          onChange={() => toggleRole(rol.value, true)}
                          className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">{rol.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    resetFormData()
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Crear Usuario
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Editar Usuario */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Editar Usuario</h2>
            <p className="text-sm text-gray-600 mb-4">{selectedUser.email}</p>
            <form onSubmit={handleUpdateUser}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre
                  </label>
                  <input
                    type="text"
                    value={editFormData.name || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Apellidos
                  </label>
                  <input
                    type="text"
                    value={editFormData.apellidos || ''}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, apellidos: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Roles *
                  </label>
                  <div className="space-y-2">
                    {ROLES_DISPONIBLES.map((rol) => (
                      <label key={rol.value} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={(editFormData.roles || []).includes(rol.value)}
                          onChange={() => toggleRole(rol.value, false)}
                          className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">{rol.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={editFormData.active}
                      onChange={(e) =>
                        setEditFormData({ ...editFormData, active: e.target.checked })
                      }
                      className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-gray-700">Usuario Activo</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false)
                    setSelectedUser(null)
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Guardar Cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Ver Actividad */}
      {showActivityModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Actividad del Usuario</h2>
            <p className="text-sm text-gray-600 mb-4">
              {selectedUser.name} ({selectedUser.email})
            </p>

            {userActivity.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay actividad registrada</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Fecha/Hora
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Acción
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Módulo
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        IP
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {userActivity.map((activity) => (
                      <tr key={activity.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                          {new Date(activity.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900">{activity.action}</td>
                        <td className="px-4 py-2 text-sm text-gray-600">{activity.module}</td>
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {activity.ip_address || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end mt-6">
              <button
                onClick={() => {
                  setShowActivityModal(false)
                  setSelectedUser(null)
                  setUserActivity([])
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </Container>
  )
}

export default TenantUsuarios

