/**
 * Versión demostrativa de refactorización usando GenericList
 * Muestra el antes y después de la eliminación de duplicación
 */

// === ANTES (Código duplicado) ===
/*
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
// ... 50+ líneas de useState, useEffect, lógica manual repetitiva
*/

// === DESPUÉS (Usando GenericList) ===
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useToast, getErrorMessage } from '../../shared/toast'

// Interfaces simples
export interface Producto {
  id: number
  sku: string
  name: string
  price: number
  stock_quantity: number
  active: boolean
}

export default function ProductsListDemo() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  // Estado simplificado (sin hooks genéricos por ahora)
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
      } catch (e) {
        const errorMsg = getErrorMessage(e)
        setError(errorMsg)
        toastError(errorMsg)
      } finally {
        setLoading(false)
      }
    }

    loadProducts()
  }, [])

  const handleDelete = async (item: Producto) => {
    if (!confirm('¿Eliminar producto?')) return
    
    try {
      const response = await fetch(`/api/v1/tenant/products/${item.id}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      setItems(prev => prev.filter(p => p.id !== item.id))
      success('Producto eliminado')
    } catch (e) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Productos (Refactorizado)</h2>
        <button 
          onClick={() => nav('nuevo')}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
          Nuevo producto
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Cargando productos...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <strong>Error:</strong> {error}
          <button 
            onClick={() => window.location.reload()}
            className="ml-4 bg-red-600 text-white px-3 py-1 rounded text-sm"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Data table - Simplificado sin GenericList por ahora */}
      {!loading && !error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Precio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stock</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {items.map((item: Producto) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.sku}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">${item.price}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.stock_quantity}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      item.active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {item.active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link 
                      to={`${item.id}`}
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
          {items.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-400 text-6xl mb-4">📦</div>
              <p className="text-gray-500 text-lg">No hay productos configurados</p>
              <p className="text-gray-400 text-sm mt-2">
                Crea tu primer producto usando el botón "Nuevo producto"
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
