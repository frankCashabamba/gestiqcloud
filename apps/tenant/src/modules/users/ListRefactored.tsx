/**
 * Versión refactorizada de usuarios usando GenericList
 * Elimina toda la duplicación de estado y lógica CRUD
 */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GenericList, type ColumnConfig, type ActionConfig } from '@crud-components'
import { useToast } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/AuthContext'
import ProtectedButton from '../../components/ProtectedButton'
import PermissionDenied from '../../components/PermissionDenied'

// Props para PermissionDenied
interface PermissionDeniedProps {
  permission?: string
}

// Componente PermissionDenied simplificado
const PermissionDeniedComponent: React.FC<PermissionDeniedProps> = ({ permission }) => {
  return (
    <div className="text-center py-8">
      <div className="text-red-600 text-lg mb-4">🚫 {permission ? 'Permission Denied' : 'Access Denied'}</div>
      <p className="text-gray-600">No tienes permisos para acceder a esta sección.</p>
    </div>
  )
}

// Tipos básicos
export interface Usuario {
  id: number
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  roles?: string[]
  created_at?: string
  last_login?: string
}

export default function UsuariosListRefactored() {
  const { t } = useTranslation(['users', 'common'])
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const { profile } = useAuth()

  // Verificar permisos
  const isAdmin = Boolean((profile as any)?.es_admin_empresa) ||
                 Boolean((profile as any)?.is_company_admin) ||
                 Boolean(profile?.roles?.includes('admin'))

  // Configuración de columnas
  const columns: ColumnConfig<Usuario>[] = [
    {
      key: 'email',
      label: t('Email'),
      sortable: true,
      filterable: true,
      render: (value, item) => (
        <Link to={`${item.id}`} className="text-blue-600 hover:text-blue-900">
          {value}
        </Link>
      )
    },
    {
      key: 'first_name',
      label: t('Nombre'),
      sortable: true,
      filterable: true
    },
    {
      key: 'last_name',
      label: t('Apellido'),
      sortable: true,
      filterable: true
    },
    {
      key: 'is_active',
      label: t('Estado'),
      sortable: true,
      filterable: true,
      render: (value) => (
        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
          value 
            ? 'bg-green-100 text-green-800' 
            : 'bg-red-100 text-red-800'
        }`}>
          {value ? t('Activo') : t('Inactivo')}
        </span>
      )
    },
    {
      key: 'created_at',
      label: t('Fecha creación'),
      sortable: true,
      render: (value) => value ? new Date(value).toLocaleDateString() : '-'
    },
    {
      key: 'last_login',
      label: t('Último login'),
      sortable: true,
      render: (value) => value ? new Date(value).toLocaleDateString() : t('Nunca')
    }
  ]

  // Configuración de acciones
  const actions: ActionConfig<Usuario>[] = [
    {
      key: 'edit',
      label: t('Editar'),
      variant: 'primary',
      href: (item) => `${item.id}`
    },
    {
      key: 'delete',
      label: t('Eliminar'),
      variant: 'danger',
      disabled: () => !isAdmin,
      onClick: async (item) => {
        if (!confirm(t('confirm_delete_user'))) return
        
        try {
          await fetch(`/api/v1/tenant/users/${item.id}`, {
            method: 'DELETE'
          })
          success(t('user_deleted'))
        } catch (error) {
          toastError(error instanceof Error ? error.message : t('error_deleting_user'))
        }
      }
    }
  ]

  // Callbacks
  const handleSuccess = (action: string, data: any) => {
    if (action === 'delete') {
      success(t('user_deleted'))
    }
  }

  const handleError = (error: string) => {
    toastError(error)
  }

  const handleNewItem = () => {
    nav('nuevo')
  }

  // Verificar permisos de lectura
  if (!profile?.roles?.includes('admin') && !profile?.roles?.includes('users.read')) {
    return <PermissionDenied />
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('users')}</h2>
        <ProtectedButton 
          permission="users.create"
          onClick={handleNewItem}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          {t('new_user')}
        </ProtectedButton>
      </div>

      <GenericList<Usuario>
        endpoint="/api/v1/tenant/users"
        schema={{} as any} // Schema simplificado por ahora
        columns={columns}
        actions={actions}
        title={t('users')}
        subtitle={t('users_management')}
        emptyMessage={t('no_users_found')}
        loadingMessage={t('loading_users')}
        errorMessage={t('error_loading_users')}
        searchable={true}
        filterable={true}
        sortable={true}
        pagination={true}
        defaultPerPage={20}
        perPageOptions={[10, 20, 50, 100]}
        onSuccess={handleSuccess}
        onError={handleError}
        className="bg-white rounded-lg shadow"
        headerClassName="border-b border-gray-200 pb-4"
        rowClassName={(item, index) => 
          index % 2 === 0 ? 'bg-gray-50' : 'bg-white'
        }
      />
    </div>
  )
}
