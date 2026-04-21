/**
 * ProductList - Componente específico para productos
 * Simple, legible y sin sobreingeniería
 */
import React, { useState, useEffect, useCallback, useRef, memo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { useCurrency } from '../../hooks/useCurrency'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import PermissionDenied from '../../components/PermissionDenied'
import type { Producto } from '@api-types/schemas'

// Componente memoizado para acciones de producto - evita renders innecesarios
const ProductActions = memo(({ 
  product, 
  onEdit, 
  onDelete, 
  deletingIds, 
  t 
}: {
  product: Producto
  onEdit: (product: Producto) => void
  onDelete: (product: Producto) => void
  deletingIds: Set<string>
  t: (key: string) => string
}) => {
  const handleEdit = useCallback(() => {
    onEdit(product)
  }, [product, onEdit])
  
  const handleDelete = useCallback(() => {
    onDelete(product)
  }, [product, onDelete])
  
  const isDeleting = deletingIds.has(product.id)
  
  return (
    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
      <div className="flex gap-2">
        <button
          onClick={handleEdit}
          className="text-blue-600 hover:text-blue-900"
        >
          {t('Editar')}
        </button>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className={`${
            isDeleting
              ? 'text-gray-400 cursor-not-allowed'
              : 'text-red-600 hover:text-red-900'
          }`}
        >
          {isDeleting ? 'Eliminando...' : t('Eliminar')}
        </button>
      </div>
    </td>
  )
})

ProductActions.displayName = 'ProductActions'

export default function ProductList() {
  const { t } = useTranslation(['products', 'common'])
  const { formatCurrency } = useCurrency()
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const checkPermission = usePermission()

  // Estado simple - sin abstracciones complejas
  const [products, setProducts] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Loading states específicos para prevenir race conditions
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
  
  // AbortController para cancelar peticiones pendientes
  const abortControllerRef = useRef<AbortController | null>(null)

  // Verificar permisos
  if (!checkPermission('products.read')) {
    return <PermissionDenied permission="products.read" />
  }

  // Fetch simple - sin useCRUD genérico (movido fuera para evitar re-renders)
  const fetchProducts = useCallback(async () => {
    // Cancelar petición anterior si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    // Crear nuevo AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch('/api/v1/tenant/products', {
        signal: abortController.signal
      })
      
      // Verificar si la petición fue cancelada
      if (abortController.signal.aborted) {
        return
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      
      // Verificar nuevamente si fue cancelada después del parse
      if (abortController.signal.aborted) {
        return
      }
      
      setProducts(data.items || [])
    } catch (err) {
      // Ignorar errores de aborto (peticiones canceladas)
      if (err instanceof Error && err.name === 'AbortError') {
        return
      }
      
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido'
      setError(errorMsg)
      toastError(errorMsg)
    } finally {
      // Limpiar controller si es la petición actual
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null
        setLoading(false)
      }
    }
  }, [toastError]) // Solo dependencia real

  // Cargar datos al montar - dependencias correctas
  useEffect(() => {
    fetchProducts()
    
    // Cleanup function para cancelar peticiones pendientes al unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
    }
  }, [fetchProducts])

  // Acciones simples
  const handleEdit = (product: Producto) => {
    nav(`${product.id}`)
  }

  const handleDelete = async (product: Producto) => {
    if (!confirm(t('confirm_delete_product'))) return
    
    // Prevenir múltiples clicks
    if (deletingIds.has(product.id)) return
    
    try {
      // Agregar ID a loading state
      setDeletingIds(prev => new Set(prev).add(product.id))
      
      const response = await fetch(`/api/v1/tenant/products/${product.id}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      success(t('product_deleted'))
      fetchProducts() // Refrescar lista
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error al eliminar'
      toastError(errorMsg)
    } finally {
      // Remover ID del loading state
      setDeletingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(product.id)
        return newSet
      })
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="text-center p-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">{t('loading_products')}</p>
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
          onClick={fetchProducts}
        >
          Reintentar
        </button>
      </div>
    )
  }

  // Empty state
  if (products.length === 0) {
    return (
      <div className="text-center p-8">
        <div className="text-gray-400 text-6xl mb-4">ð¦</div>
        <p className="text-gray-500 mb-4">{t('no_products_found')}</p>
        {checkPermission('products.create') && (
          <ProtectedButton
            permission="products.create"
            onClick={() => nav('nuevo')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            {t('new_product')}
          </ProtectedButton>
        )}
      </div>
    )
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('products')}</h2>
        {checkPermission('products.create') && (
          <ProtectedButton
            permission="products.create"
            onClick={() => nav('nuevo')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            {t('new_product')}
          </ProtectedButton>
        )}
      </div>

      {/* Table simple - sin ColumnConfig complejo */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                SKU
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Nombre')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Precio')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Stock')}
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
            {products.map((product) => (
              <tr key={product.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {product.sku}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {product.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency(product.price)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {product.stock_quantity || 0}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    product.active 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {product.active ? t('Activo') : t('Inactivo')}
                  </span>
                </td>
                <ProductActions
                  product={product}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  deletingIds={deletingIds}
                  t={t}
                />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
