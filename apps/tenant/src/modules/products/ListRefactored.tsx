/**
 * Versión refactorizada de productos usando GenericList
 * Elimina toda la duplicación de estado y lógica CRUD
 */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GenericList, type ColumnConfig, type ActionConfig } from '@crud-components'
import { useToast } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { useCurrency } from '../../hooks/useCurrency'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import PermissionDenied from '../../components/PermissionDenied'
import { ProductoSchema, type Producto } from '@api-types/schemas'

export default function ProductsListRefactored() {
  const { t } = useTranslation(['products', 'common'])
  const { formatCurrency } = useCurrency()
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const { hasPermission } = usePermission()

  // Verificar permisos
  if (!hasPermission('products.read')) {
    return <PermissionDenied />
  }

  // Configuración de columnas
  const columns: ColumnConfig<Producto>[] = [
    {
      key: 'sku',
      label: t('SKU'),
      sortable: true,
      filterable: true,
      width: '120px'
    },
    {
      key: 'name',
      label: t('Nombre'),
      sortable: true,
      filterable: true,
      render: (value, item) => (
        <Link to={`${item.id}`} className="text-blue-600 hover:text-blue-900">
          {value}
        </Link>
      )
    },
    {
      key: 'category_name',
      label: t('Categoría'),
      sortable: true,
      filterable: true,
      render: (value) => value || t('Sin categoría')
    },
    {
      key: 'price',
      label: t('Precio'),
      sortable: true,
      filterable: true,
      align: 'right',
      render: (value) => formatCurrency(value)
    },
    {
      key: 'stock_quantity',
      label: t('Stock'),
      sortable: true,
      filterable: true,
      align: 'right',
      render: (value) => (
        <span className={value <= 10 ? 'text-red-600 font-semibold' : 'text-green-600'}>
          {value}
        </span>
      )
    },
    {
      key: 'active',
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
    }
  ]

  // Configuración de acciones
  const actions: ActionConfig<Producto>[] = [
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
      disabled: (item) => !hasPermission('products.delete'),
      onClick: async (item) => {
        if (!confirm(t('confirm_delete_product'))) return
        
        try {
          await fetch(`/api/v1/tenant/products/${item.id}`, {
            method: 'DELETE'
          })
          success(t('product_deleted'))
        } catch (error) {
          toastError(error instanceof Error ? error.message : t('error_deleting_product'))
        }
      }
    }
  ]

  // Callbacks
  const handleSuccess = (action: string, data: any) => {
    if (action === 'delete') {
      success(t('product_deleted'))
    }
  }

  const handleError = (error: string) => {
    toastError(error)
  }

  const handleNewItem = () => {
    nav('nuevo')
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('products')}</h2>
        <ProtectedButton 
          permission="products.create"
          onClick={handleNewItem}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          {t('new_product')}
        </ProtectedButton>
      </div>

      <GenericList<Producto>
        endpoint="/api/v1/tenant/products"
        schema={ProductoSchema}
        columns={columns}
        actions={actions}
        title={t('products')}
        subtitle={t('products_description')}
        emptyMessage={t('no_products_found')}
        loadingMessage={t('loading_products')}
        errorMessage={t('error_loading_products')}
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
