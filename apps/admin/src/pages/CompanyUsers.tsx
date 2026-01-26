// src/pages/CompanyUsuarios.tsx

import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Container } from './Container'
import {
  listCompanyUsers,
  createCompanyUser,
  updateCompanyUser,
  resetUserPassword,
  toggleUserActive,
  deleteUser,
  getUserActivity,
  CompanyUser,
  CreateUserPayload,
  UpdateUserPayload,
  UserActivity,
} from '../services/company-users'
import { getEmpresa } from '../services/empresa'
import { useToast } from '../shared/toast'

const ROLES_DISPONIBLES = [
  { value: 'owner', label: 'Owner (Full Admin)' },
  { value: 'manager', label: 'Manager (Management)' },
  { value: 'cajero', label: 'Cashier/Operator (POS)' },
  { value: 'contable', label: 'Accountant (Billing)' },
  { value: 'vendedor', label: 'Salesperson (Sales)' },
  { value: 'almacen', label: 'Warehouse (Stock)' },
]

export const CompanyUsuarios: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { show: showToast } = useToast()

  const [empresa, setEmpresa] = useState<any>(null)
  const [usuarios, setUsuarios] = useState<CompanyUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filtroActivo, setFiltroActivo] = useState<'all' | 'activo' | 'inactivo'>('all')

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showActivityModal, setShowActivityModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<CompanyUser | null>(null)
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
        listCompanyUsers(id),
      ])
      setEmpresa(empresaData)
      setUsuarios(usersData.users || usersData || [])
    } catch (err: any) {
      showToast('Error loading data', 'error')
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
      showToast('Email, name and password are required', 'error')
      return
    }
    if (formData.roles.length === 0) {
      showToast('You must assign at least one role', 'error')
      return
    }

    try {
      const result = await createCompanyUser(id, formData)
      showToast('User created successfully. Credentials sent via email.', 'success')
      setShowCreateModal(false)
      resetFormData()
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error creating user', 'error')
      console.error(err)
    }
  }

  // Actualizar usuario
  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !selectedUser) return

    if (!editFormData.roles || editFormData.roles.length === 0) {
      showToast('You must assign at least one role', 'error')
      return
    }

    try {
      await updateCompanyUser(id, selectedUser.id, editFormData)
      showToast('User updated successfully', 'success')
      setShowEditModal(false)
      setSelectedUser(null)
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error updating user', 'error')
      console.error(err)
    }
  }

  // Resetear password
  const handleResetPassword = async (user: CompanyUser) => {
    if (!id) return
    if (!confirm(`Reset password for ${user.email}? A new password will be sent via email.`)) {
      return
    }

    try {
      await resetUserPassword(id, user.id)
      showToast('Password reset. New password sent via email.', 'success')
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error resetting password', 'error')
      console.error(err)
    }
  }

  // Toggle activo
  const handleToggleActive = async (user: CompanyUser) => {
    if (!id) return
    const action = user.active ? 'deactivate' : 'activate'
    if (!confirm(`Confirm ${action} user ${user.email}?`)) {
      return
    }

    try {
      await toggleUserActive(id, user.id, !user.active)
      showToast(`User ${action}d successfully`, 'success')
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || `Error ${action} user`, 'error')
      console.error(err)
    }
  }

  // Eliminar usuario
  const handleDeleteUser = async (user: CompanyUser) => {
    if (!id) return
    if (!confirm(`DELETE user ${user.email}? This action CANNOT be undone.`)) {
      return
    }

    try {
      await deleteUser(id, user.id)
      showToast('User deleted successfully', 'success')
      await loadData()
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Error deleting user', 'error')
      console.error(err)
    }
  }

  // Ver actividad
  const handleViewActivity = async (user: CompanyUser) => {
    try {
      const activity = await getUserActivity(user.id)
      setUserActivity(activity.activity || activity || [])
      setSelectedUser(user)
      setShowActivityModal(true)
    } catch (err: any) {
      showToast('Error loading activity', 'error')
      console.error(err)
    }
  }

  // Abrir modal de edición
  const handleOpenEditModal = (user: CompanyUser) => {
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
        <Link to="/admin/companies" className="hover:text-blue-600">Companies</Link>
        {' > '}
        {empresa && <span className="font-medium">{empresa.name}</span>}
        {' > '}
        <span className="font-medium">Users</span>
      </nav>

      {/* Header */}
      <div className="admin-header">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Company Users</h1>
          {empresa && <p className="text-gray-600 text-sm mt-1">{empresa.name} (ID: {id})</p>}
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary"
        >
          ➕ New User
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-4 mb-6">
        <input
          type="search"
          placeholder="Search by email or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input"
        />
        <select
          value={filtroActivo}
          onChange={(e) => setFiltroActivo(e.target.value as any)}
          className="input"
        >
          <option value="all">All</option>
          <option value="activo">Active</option>
          <option value="inactivo">Inactive</option>
        </select>
      </div>

      {/* Lista de usuarios */}
      {loading ? (
        <p className="text-gray-500">Loading users...</p>
      ) : usuariosFiltrados.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No users to display</p>
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
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Roles
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Login
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
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
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {user.ultima_conexion
                      ? new Date(user.ultima_conexion).toLocaleString()
                      : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleOpenEditModal(user)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Edit"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleResetPassword(user)}
                        className="text-yellow-600 hover:text-yellow-900"
                        title="Reset Password"
                      >
                        🔑
                      </button>
                      <button
                        onClick={() => handleToggleActive(user)}
                        className={user.active ? 'text-orange-600 hover:text-orange-900' : 'text-green-600 hover:text-green-900'}
                        title={user.active ? 'Deactivate' : 'Activate'}
                      >
                        {user.active ? '🚫' : '✅'}
                      </button>
                      <button
                        onClick={() => handleViewActivity(user)}
                        className="text-purple-600 hover:text-purple-900"
                        title="View Activity"
                      >
                        📊
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user)}
                        className="text-red-600 hover:text-red-900"
                        title="Delete"
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
            <h2 className="text-xl font-bold mb-4">Create New User</h2>
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
                    Name *
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
                    Last Name
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
                  <p className="text-xs text-gray-500 mt-1">Min. 8 characters</p>
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
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Create User
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
            <h2 className="text-xl font-bold mb-4">Edit User</h2>
            <p className="text-sm text-gray-600 mb-4">{selectedUser.email}</p>
            <form onSubmit={handleUpdateUser}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name
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
                    Last Name
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
                    <span className="text-sm font-medium text-gray-700">Active User</span>
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
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Save Changes
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
            <h2 className="text-xl font-bold mb-4">User Activity</h2>
            <p className="text-sm text-gray-600 mb-4">
              {selectedUser.name} ({selectedUser.email})
            </p>

            {userActivity.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No activity recorded</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Date/Time
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Action
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Module
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
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </Container>
  )
}

export default CompanyUsuarios
