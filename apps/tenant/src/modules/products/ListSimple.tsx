/**
 * Versión refactorizada de productos usando GenericList (simplificada)
 * Elimina toda la duplicación de estado y lógica CRUD
 */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { useCurrency } from '../../hooks/useCurrency'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import PermissionDenied from '../../components/PermissionDenied'

// Tipos básicos
export interface Producto {
  id: number
  sku: string
  name: string
  description?: string
  price: number
  cost?: number
  category_id?: number
  category_name?: string
  stock_quantity?: number
  active: boolean
  created_at?: string
  updated_at?: string
}

export default function ProductsListSimple() {
  const { t } = useTranslation(['products', 'common'])
  const { formatCurrency } = useCurrency()
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const hasPermission = usePermission()

  // Estado local simplificado (sin useCRUD por ahora para evitar errores)
  const [items, setItems] = React.useState<Producto[]>([])
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // Cargar datos
  React.useEffect(() => {
    const loadProducts = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch('/api/v1/tenant/products')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = await response.json()
        setItems(data.items || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading products')
      } finally {
        setLoading(false)
      }
    }

    loadProducts()
  }, [])

  // Verificar permisos
  if (!hasPermission('products.read')) {
    return <PermissionDenied permission="products.read" />
  }

  // Configuración de columnas
  const columns = [
    { key: 'sku', label: t('SKU'), width: '120px' },
    { key: 'name', label: t('Nombre') },
    { key: 'category_name', label: t('Categoría'), render: (val) => val || t('Sin categoría') },
    { key: 'price', label: t('Precio'), align: 'right', render: (val) => formatCurrency(val) },
    { key: 'stock_quantity', label: t('Stock'), align: 'right' },
    {
      key: 'active',
      label: t('Estado'),
      render: (val) => (
        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
          val ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {val ? t('Activo') : t('Inactivo')}
        </span>
      )
    }
  ]

  // Manejadores
  const handleDelete = async (item: Producto) => {
    if (!confirm(t('confirm_delete_product'))) return

    try {
      const response = await fetch(`/api/v1/tenant/products/${item.id}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      setItems(prev => prev.filter(p => p.id !== item.id))
      success(t('product_deleted'))
    } catch (err) {
      toastError(err instanceof Error ? err.message : t('error_deleting_product'))
    }
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

      {/* Loading state */}
      {loading && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">{t('loading')}...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <strong>Error:</strong> {error}
          <button
            onClick={() => window.location.reload()}
            className="ml-4 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
          >
            {t('retry')}
          </button>
        </div>
      )}

      {/* Data table */}
      {!loading && !error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {columns.map(col => (
                  <th key={col.key} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {items.map((item: Producto) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  {columns.map(col => (
                    <td key={col.key} className="px-6 py-4 whitespace-nowrap text-sm">
                      {col.render ? col.render(item[col.key as keyof Producto]) : item[col.key as keyof Producto]}
                    </td>
                  ))}
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link
                      to={`${item.id}`}
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      {t('edit')}
                    </Link>
                    <button
                      onClick={() => handleDelete(item)}
                      className="text-red-600 hover:text-red-900"
                    >
                      {t('delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Empty state */}
          {items.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-400 text-6xl mb-4">📦</div>
              <p className="text-gray-500 text-lg">{t('no_products_found')}</p>
              <p className="text-gray-400 text-sm mt-2">
                {t('create_first_product')}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
