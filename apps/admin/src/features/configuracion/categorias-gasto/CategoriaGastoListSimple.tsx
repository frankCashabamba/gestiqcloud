/**
 * Versión refactorizada simplificada - Demostración del uso de packages
 * Elimina duplicación de estado y lógica CRUD
 */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCRUD, usePagination, useFilters } from '@ui-hooks'
import { useToast } from '../../../shared/toast'

// Tipos básicos (sin Zod por ahora para simplicidad)
export interface CategoriaGasto {
  id: number
  code: string
  name: string
  parent_code: string | null
  active: boolean
}

export default function CategoriaGastoListSimple() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  // Hook CRUD genérico - maneja todo el estado automáticamente
  const crud = useCRUD<CategoriaGasto>({
    endpoint: '/api/v1/admin/categorias-gasto',
    schema: {} as any, // Schema simplificado por ahora
    onSuccess: (action, data) => {
      if (action === 'delete') {
        success('Categoría de gasto eliminada')
      }
    },
    onError: (error) => {
      toastError(error)
    }
  })

  // Navegación a nuevo item
  const handleNewItem = () => {
    nav('nuevo')
  }

  // Manejador de eliminación
  const handleDelete = async (item: CategoriaGasto) => {
    if (!confirm('¿Eliminar categoría de gasto?')) return
    
    await crud.deleteItem(String(item.id))
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Categorías de gasto</h2>
        <button 
          onClick={handleNewItem}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Nueva categoría
        </button>
      </div>

      {/* Loading state */}
      {crud.loading && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Cargando categorías...</p>
        </div>
      )}

      {/* Error state */}
      {crud.error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <strong>Error:</strong> {crud.error}
          <button 
            onClick={crud.refreshItems}
            className="ml-4 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Data table */}
      {!crud.loading && !crud.error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Código
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Categoría padre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {crud.items.map((item: CategoriaGasto) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.code}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.parent_code || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      item.active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {item.active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link 
                      to={`${item.id}/editar`}
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      Editar
                    </Link>
                    <button 
                      onClick={() => handleDelete(item)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Empty state */}
          {crud.items.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-400 text-6xl mb-4">📋</div>
              <p className="text-gray-500 text-lg">No hay categorías de gasto configuradas</p>
              <p className="text-gray-400 text-sm mt-2">
                Crea tu primera categoría usando el botón "Nueva categoría"
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
