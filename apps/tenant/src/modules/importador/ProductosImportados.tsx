import React, { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import ImportadorLayout from './components/ImportadorLayout'

interface ProductoImportado {
  id: string
  idx: number
  status: string
  errors: string[]
  batch_id?: string
  // Backend may return spanish keys; keep both for safety
  sku: string | null
  codigo?: string | null
  name: string | null
  nombre?: string | null
  price: number | null
  precio?: number | string | null
  costo: number | null
  categoria: string | null
  stock: number
  unidad: string
  iva: number
  raw: Record<string, any>
  normalized: Record<string, any>
}

interface ProductosResponse {
  items: ProductoImportado[]
  total: number
  limit: number
  offset: number
}

const ProductosImportados: React.FC = () => {
  const { token, profile } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [productos, setProductos] = useState<ProductoImportado[]>([])
  const [autoMode, setAutoMode] = useState(true)
  const [targetWarehouse, setTargetWarehouse] = useState('ALM-1')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<Partial<ProductoImportado>>({})

  const batchId = searchParams.get('batch_id')
  const status = searchParams.get('status') || 'OK'
  const offset = parseInt(searchParams.get('offset') || '0', 10)
  const limit = parseInt(searchParams.get('limit') || '5000', 10)

  const fetchProductos = useCallback(async () => {
    try {
      setLoading(true)
      // Si hay batchId, usar endpoint específico; sino, listar todos
      const endpoint = batchId
        ? `/api/v1/imports/batches/${batchId}/items/products`
        : '/api/v1/imports/items/products'

      const url = new URL(endpoint, window.location.origin)
      if (status) url.searchParams.set('status', status)
      url.searchParams.set('offset', offset.toString())
      url.searchParams.set('limit', limit.toString())
      // Public endpoint requires tenant_id when RLS GUC is not set
      if (!batchId && profile?.tenant_id) {
        url.searchParams.set('tenant_id', profile.tenant_id)
      }

      const res = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!res.ok) throw new Error(`Error ${res.status}: ${res.statusText}`)

      const data: ProductosResponse = await res.json()
      setProductos(data.items)
      setTotal(data.total)
      setError(null)
    } catch (err: any) {
      console.error('Error al cargar productos:', err)
      setError(err.message || 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }, [batchId, status, offset, limit, token, profile?.tenant_id])

  useEffect(() => {
    fetchProductos()
  }, [fetchProductos])

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(productos.map((p) => p.id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSet = new Set(selectedIds)
    if (checked) {
      newSet.add(id)
    } else {
      newSet.delete(id)
    }
    setSelectedIds(newSet)
  }

  const handleEdit = (producto: ProductoImportado) => {
    setEditingId(producto.id)
    setEditValues({
      sku: producto.sku || producto.codigo || '',
      name: producto.name || producto.nombre || '',
      price: typeof producto.price === 'number' && !isNaN(producto.price)
        ? producto.price
        : (typeof producto.precio === 'string' ? parseFloat(producto.precio) : (producto.precio ?? 0)),
      costo: producto.costo,
      categoria: producto.categoria,
      stock: producto.stock,
      unidad: producto.unidad,
      iva: producto.iva,
    })
  }

  const handleSaveEdit = async () => {
    if (!editingId || !batchId) return

    try {
      const res = await fetch(`/api/v1/imports/batches/${batchId}/items/${editingId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          normalized: editValues,
        }),
      })

      if (!res.ok) throw new Error('Error al guardar')

      setEditingId(null)
      setEditValues({})
      fetchProductos()
    } catch (err: any) {
      alert(`Error: ${err.message}`)
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditValues({})
  }

  const handleEliminar = async () => {
    if (selectedIds.size === 0) {
      alert('Selecciona al menos un producto')
      return
    }

    if (!confirm(`¿Eliminar ${selectedIds.size} productos? Esta acción no se puede deshacer.`)) return

    try {
      const res = await fetch('/api/v1/imports/items/delete-multiple', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          item_ids: Array.from(selectedIds),
        }),
      })

      if (!res.ok) throw new Error('Error al eliminar')

      const result = await res.json()
      alert(`✅ ${result.deleted} productos eliminados`)

      setSelectedIds(new Set())
      fetchProductos()
    } catch (err: any) {
      alert(`Error: ${err.message}`)
    }
  }

  const handlePromover = async () => {
    if (selectedIds.size === 0) {
      alert('Selecciona al menos un producto')
      return
    }

    if (!confirm(`¿Promover ${selectedIds.size} productos al catálogo?`)) return

    try {
      // Si hay batchId, promover todo el batch; sino, promover items individuales
      const endpoint = batchId
        ? `/api/v1/imports/batches/${batchId}/promote`
        : '/api/v1/imports/items/promote'

      const url = new URL(endpoint, window.location.origin)
      if (autoMode) {
        url.searchParams.set('auto', '1')
        url.searchParams.set('target_warehouse', targetWarehouse || 'ALM-1')
        url.searchParams.set('create_warehouse', '1')
        url.searchParams.set('allow_missing_price', '1')
        url.searchParams.set('activate', '1')
      }

      const res = await fetch(url.toString(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          item_ids: Array.from(selectedIds),
        }),
      })

      if (!res.ok) throw new Error('Error al promover')

      const result = await res.json()
      console.log('🎯 Resultado de promoción:', result)

      if (result.errors && result.errors.length > 0) {
        console.error('❌ Errores en promoción:', result.errors.slice(0, 5))
        alert(`Promovidos: ${result.promoted}/${result.total}\nErrores: ${result.errors.length}\nRevisa la consola para detalles.`)
      } else {
        alert(`✅ ${result.promoted} productos promovidos exitosamente`)
      }

      setSelectedIds(new Set())
      fetchProductos()
    } catch (err: any) {
      alert(`Error: ${err.message}`)
    }
  }

  const handlePageChange = (newOffset: number) => {
    setSearchParams({ batch_id: batchId!, status, offset: newOffset.toString(), limit: limit.toString() })
  }

  if (loading && productos.length === 0) {
    return (
      <ImportadorLayout>
        <div className="flex items-center justify-center p-12">
          <div className="text-neutral-600">Cargando productos...</div>
        </div>
      </ImportadorLayout>
    )
  }

  if (error) {
    return (
      <ImportadorLayout>
        <div className="p-4">
          <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded">
            Error: {error}
          </div>
          <Link to="../" relative="path" className="text-blue-600 hover:underline mt-4 inline-block">
            ← Volver al importador
          </Link>
        </div>
      </ImportadorLayout>
    )
  }

  const allSelected = productos.length > 0 && selectedIds.size === productos.length

  return (
    <ImportadorLayout>
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              {batchId ? 'Productos del Lote' : 'Todos los Productos Importados'}
            </h1>
            <p className="text-sm text-neutral-600 mt-1">
              {total} productos · {selectedIds.size} seleccionados
              {batchId && <span className="ml-2 text-xs font-mono text-neutral-500">({batchId.slice(0, 8)})</span>}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleEliminar}
              disabled={selectedIds.size === 0}
              className="px-4 py-2 bg-rose-600 text-white rounded hover:bg-rose-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              title="Eliminar productos seleccionados"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Eliminar ({selectedIds.size})
            </button>
            <button
              onClick={handlePromover}
              disabled={selectedIds.size === 0}
              className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Promover ({selectedIds.size})
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 items-center flex-wrap">
          <label className="text-sm font-medium text-neutral-700">Estado:</label>
          <select
            value={status}
            onChange={(e) => {
              const params: Record<string, string> = { status: e.target.value, offset: '0', limit: limit.toString() }
              if (batchId) params.batch_id = batchId
              setSearchParams(params)
            }}
            className="border border-neutral-300 rounded px-3 py-1.5 text-sm"
          >
            <option value="OK">OK</option>
            <option value="READY">Listo</option>
            <option value="ERROR_VALIDATION">Con errores</option>
            <option value="PROMOTED">Promovidos</option>
          </select>

          {!batchId && (
            <span className="text-xs text-neutral-500 ml-2">
              Mostrando productos de todos los lotes importados
            </span>
          )}
        </div>

        {/* Modo automático */}
        <div className="flex items-center gap-3 p-3 border rounded bg-neutral-50">
          <label className="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" checked={autoMode} onChange={(e) => setAutoMode(e.target.checked)} />
            Modo automático (recomendado)
          </label>
          <span className="text-xs text-neutral-500">Activa productos, crea ALM-1 si falta y aplica stock inicial.</span>
          <div className="flex items-center gap-2 ml-auto">
            <label className="text-sm text-neutral-700">Almacén destino:</label>
            <input value={targetWarehouse} onChange={(e) => setTargetWarehouse(e.target.value)} className="border rounded px-2 py-1 text-sm w-28" placeholder="ALM-1" />
          </div>
        </div>

        {/* Table */}
        <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 border-b border-neutral-200">
                <tr>
                  <th className="p-3 text-left">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                      className="rounded border-neutral-300"
                    />
                  </th>
                  <th className="p-3 text-left font-semibold text-neutral-700">#</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Código</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Nombre</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Precio</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Costo</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Categoría</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Stock</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Unidad</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">IVA</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Estado</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {productos.map((producto) => {
                  const isEditing = editingId === producto.id
                  const isSelected = selectedIds.has(producto.id)

                  return (
                    <tr
                      key={producto.id}
                      className={`hover:bg-neutral-50 ${isSelected ? 'bg-blue-50' : ''} ${producto.errors.length > 0 ? 'bg-rose-50' : ''}`}
                    >
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => handleSelectOne(producto.id, e.target.checked)}
                          className="rounded border-neutral-300"
                        />
                      </td>
                      <td className="p-3 text-neutral-600">{producto.idx + 1}</td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editValues.sku || ''}
                            onChange={(e) => setEditValues({ ...editValues, sku: e.target.value })}
                            className="border border-neutral-300 rounded px-2 py-1 w-full"
                          />
                        ) : (
                          <span className="text-neutral-900 font-mono text-xs">{producto.sku || producto.codigo || '-'}</span>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editValues.name || ''}
                            onChange={(e) => setEditValues({ ...editValues, name: e.target.value })}
                            className="border border-neutral-300 rounded px-2 py-1 w-full"
                          />
                        ) : (
                          <span className="text-neutral-900">{producto.name || producto.nombre || '-'}</span>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.01"
                            value={editValues.price ?? ''}
                            onChange={(e) => setEditValues({ ...editValues, price: parseFloat(e.target.value) })}
                            className="border border-neutral-300 rounded px-2 py-1 w-20"
                          />
                        ) : (
                          <span className="text-neutral-900">
                            ${(() => {
                              if (typeof producto.price === 'number') return producto.price.toFixed(2)
                              const p = (typeof producto.precio === 'string') ? parseFloat(producto.precio) : (producto.precio as number | null)
                              const v = typeof p === 'number' && !isNaN(p) ? p : (parseFloat(String(producto.price || 0)) || 0)
                              return v.toFixed(2)
                            })()}
                          </span>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.01"
                            value={editValues.costo ?? ''}
                            onChange={(e) => setEditValues({ ...editValues, costo: parseFloat(e.target.value) })}
                            className="border border-neutral-300 rounded px-2 py-1 w-20"
                          />
                        ) : (
                          <span className="text-neutral-600">
                            ${typeof producto.costo === 'number' ? producto.costo.toFixed(2) : (parseFloat(String(producto.costo || 0)) || 0).toFixed(2)}
                          </span>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editValues.categoria || ''}
                            onChange={(e) => setEditValues({ ...editValues, categoria: e.target.value })}
                            className="border border-neutral-300 rounded px-2 py-1 w-full"
                          />
                        ) : (
                          <span className="text-neutral-700">{producto.categoria || '—'}</span>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="number"
                            value={editValues.stock ?? 0}
                            onChange={(e) => setEditValues({ ...editValues, stock: parseInt(e.target.value) })}
                            className="border border-neutral-300 rounded px-2 py-1 w-16"
                          />
                        ) : (
                          <span className="text-neutral-900">{producto.stock}</span>
                        )}
                      </td>
                      <td className="p-3">
                        <span className="text-neutral-600 text-xs">{producto.unidad}</span>
                      </td>
                      <td className="p-3">
                        <span className="text-neutral-600">{producto.iva}%</span>
                      </td>
                      <td className="p-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            producto.status === 'OK'
                              ? 'bg-emerald-100 text-emerald-800'
                              : producto.status === 'ERROR_VALIDATION'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-neutral-100 text-neutral-700'
                          }`}
                        >
                          {producto.status}
                        </span>
                        {producto.errors.length > 0 && (
                          <div className="text-xs text-rose-600 mt-1">
                            {producto.errors.join(', ')}
                          </div>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <div className="flex gap-1">
                            <button
                              onClick={handleSaveEdit}
                              className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                            >
                              Guardar
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="px-2 py-1 border border-neutral-300 text-xs rounded hover:bg-neutral-50"
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleEdit(producto)}
                            className="px-2 py-1 text-blue-600 hover:underline text-xs"
                          >
                            Editar
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {total > limit && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-neutral-600">
              Mostrando {offset + 1}-{Math.min(offset + limit, total)} de {total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1.5 border border-neutral-300 rounded hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>
              <button
                onClick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1.5 border border-neutral-300 rounded hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </ImportadorLayout>
  )
}

export default ProductosImportados
