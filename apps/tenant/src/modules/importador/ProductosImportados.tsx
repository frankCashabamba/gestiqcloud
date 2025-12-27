import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import ImportadorLayout from './components/ImportadorLayout'
import { apiFetch } from '../../lib/http'
import { listAllProductItems, listProductItems, patchItem } from './services/importsApi'

interface ProductoImportado {
  id: string
  idx: number
  status: string
  errors: string[]
  batch_id?: string
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
  const [showZeroStockNotice, setShowZeroStockNotice] = useState(false)

  const batchId = searchParams.get('batch_id')
  const statusParam = searchParams.get('status')
  const isZeroStockFilter = statusParam === 'SIN_STOCK'
  const status = isZeroStockFilter ? undefined : statusParam ? (statusParam !== 'all' ? statusParam : undefined) : 'OK'
  const offset = parseInt(searchParams.get('offset') || '0', 10)
  const limit = parseInt(searchParams.get('limit') || '5000', 10)

  const fetchProductos = useCallback(async () => {
    try {
      setLoading(true)
      if (batchId) {
        const data = await listProductItems(batchId, { status, limit, offset, authToken: token || undefined })
        setProductos(data.items as ProductoImportado[])
        setTotal(data.total || data.items.length)
      } else {
        const data = await listAllProductItems({
          status,
          limit,
          offset,
          tenantId: profile?.tenant_id,
          authToken: token || undefined,
        })
        setProductos(data.items as ProductoImportado[])
        setTotal(data.total || data.items.length)
      }
      setError(null)
    } catch (err: any) {
      console.error('Error loading products:', err)
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [batchId, status, offset, limit, token, profile?.tenant_id])

  useEffect(() => {
    fetchProductos()
  }, [fetchProductos])

  const zeroStockCount = useMemo(() => {
    return productos.filter((p) => (p.stock ?? 0) <= 0).length
  }, [productos])

  const displayedProductos = useMemo(() => {
    if (!isZeroStockFilter) return productos
    return productos.filter((p) => (p.stock ?? 0) <= 0)
  }, [productos, isZeroStockFilter])

  const editingBatchId = useMemo(() => {
    if (batchId) return batchId
    if (!editingId) return null
    const item = productos.find((p) => p.id === editingId)
    return item?.batch_id || null
  }, [batchId, editingId, productos])

  useEffect(() => {
    setShowZeroStockNotice(zeroStockCount > 0)
  }, [zeroStockCount])

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(displayedProductos.map((p) => p.id)))
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
      price:
        typeof producto.price === 'number' && !isNaN(producto.price)
          ? producto.price
          : typeof producto.precio === 'string'
          ? parseFloat(producto.precio)
          : producto.precio ?? 0,
      costo: producto.costo,
      categoria: producto.categoria,
      stock: producto.stock,
      unidad: producto.unidad,
      iva: producto.iva,
    })
  }

  const handleSaveEdit = async () => {
    if (!editingId) return
    if (!editingBatchId) {
      alert('Could not determine batch for this item')
      return
    }

    try {
      for (const [field, value] of Object.entries(editValues)) {
        await patchItem(editingBatchId, editingId, field, value as any)
      }

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
      alert('Select at least one product')
      return
    }

    if (!confirm(`Delete ${selectedIds.size} products? This cannot be undone.`)) return

    try {
      const result = await apiFetch<{ deleted: number }>('/api/v1/tenant/imports/items/delete-multiple', {
        method: 'POST',
        authToken: token || undefined,
        body: JSON.stringify({
          item_ids: Array.from(selectedIds),
        }),
      })
      alert(`${result.deleted} products deleted`)

      setSelectedIds(new Set())
      fetchProductos()
    } catch (err: any) {
      alert(`Error: ${err.message}`)
    }
  }

  const handlePromover = async () => {
    if (selectedIds.size === 0) {
      alert('Select at least one product')
      return
    }

    const zeroStockSelected = productos.filter((p) => selectedIds.has(p.id) && (p.stock ?? 0) <= 0).length
    if (zeroStockSelected > 0) {
      if (!confirm(`There are ${zeroStockSelected} products with zero stock. Promote anyway?`)) return
    }

    if (!confirm(`Promote ${selectedIds.size} products to the catalog?`)) return

    try {
      const endpoint = batchId
        ? `/api/v1/tenant/imports/batches/${batchId}/promote`
        : '/api/v1/tenant/imports/items/promote'

      const url = new URL(endpoint, window.location.origin)
      if (autoMode) {
        url.searchParams.set('auto', '1')
        url.searchParams.set('target_warehouse', targetWarehouse || 'ALM-1')
        url.searchParams.set('create_warehouse', '1')
        url.searchParams.set('allow_missing_price', '1')
        url.searchParams.set('activate', '1')
      }

      const result = await apiFetch<{ promoted: number; total: number; errors?: any[] }>(url.pathname + url.search, {
        method: 'POST',
        authToken: token || undefined,
        body: JSON.stringify({
          item_ids: Array.from(selectedIds),
        }),
      })
      console.log('Promotion result:', result)

      if (result.errors && result.errors.length > 0) {
        console.error('Promotion errors:', result.errors.slice(0, 5))
        alert(`Promoted: ${result.promoted}/${result.total}\nErrors: ${result.errors.length}\nCheck console for details.`)
      } else {
        alert(`${result.promoted} products promoted successfully`)
      }

      setSelectedIds(new Set())
      fetchProductos()
    } catch (err: any) {
      alert(`Error: ${err.message}`)
    }
  }

  const handlePageChange = (newOffset: number) => {
    const params: Record<string, string> = {
      offset: newOffset.toString(),
      limit: limit.toString(),
      status: statusParam || 'OK',
    }
    if (batchId) params.batch_id = batchId
    setSearchParams(params)
  }

  if (loading && productos.length === 0) {
    return (
      <ImportadorLayout>
        <div className="flex items-center justify-center p-12">
          <div className="text-neutral-600">Loading products...</div>
        </div>
      </ImportadorLayout>
    )
  }

  if (error) {
    return (
      <ImportadorLayout>
        <div className="p-4">
          <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded">Error: {error}</div>
          <Link to="../" relative="path" className="text-blue-600 hover:underline mt-4 inline-block">
            Back to importer
          </Link>
        </div>
      </ImportadorLayout>
    )
  }

  const displayedTotal = isZeroStockFilter ? displayedProductos.length : total
  const allSelected = displayedProductos.length > 0 && selectedIds.size === displayedProductos.length

  return (
    <ImportadorLayout>
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              {batchId ? 'Batch products' : 'All imported products'}
            </h1>
            <p className="text-sm text-neutral-600 mt-1">
              {displayedTotal} products | {selectedIds.size} selected
              {batchId && <span className="ml-2 text-xs font-mono text-neutral-500">({batchId.slice(0, 8)})</span>}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleEliminar}
              disabled={selectedIds.size === 0}
              className="px-4 py-2 bg-rose-600 text-white rounded hover:bg-rose-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              title="Delete selected products"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete ({selectedIds.size})
            </button>
            <button
              onClick={handlePromover}
              disabled={selectedIds.size === 0}
              className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Promote ({selectedIds.size})
            </button>
          </div>
        </div>

        <div className="flex gap-2 items-center flex-wrap">
          <label className="text-sm font-medium text-neutral-700">Status:</label>
          <select
            value={statusParam || 'OK'}
            onChange={(e) => {
              const params: Record<string, string> = { status: e.target.value, offset: '0', limit: limit.toString() }
              if (batchId) params.batch_id = batchId
              setSearchParams(params)
            }}
            className="border border-neutral-300 rounded px-3 py-1.5 text-sm"
          >
            <option value="all">All</option>
            <option value="OK">OK</option>
            <option value="READY">Ready</option>
            <option value="ERROR_VALIDATION">With errors</option>
            <option value="PROMOTED">Promoted</option>
            <option value="SIN_STOCK">Zero stock</option>
          </select>

          {!batchId && <span className="text-xs text-neutral-500 ml-2">Showing products from all batches</span>}
        </div>

        <div className="flex items-center gap-3 p-3 border rounded bg-neutral-50">
          <label className="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" checked={autoMode} onChange={(e) => setAutoMode(e.target.checked)} />
            Auto mode (recommended)
          </label>
          <span className="text-xs text-neutral-500">
            Activates products, creates ALM-1 if missing, and applies initial stock.
          </span>
          <div className="flex items-center gap-2 ml-auto">
            <label className="text-sm text-neutral-700">Target warehouse:</label>
            <input
              value={targetWarehouse}
              onChange={(e) => setTargetWarehouse(e.target.value)}
              className="border rounded px-2 py-1 text-sm w-28"
              placeholder="ALM-1"
            />
          </div>
        </div>

        {showZeroStockNotice && (
          <div className="flex items-center justify-between gap-3 p-3 border border-amber-200 bg-amber-50 rounded">
            <div className="text-sm text-amber-800">There are {zeroStockCount} products with zero stock.</div>
            <button type="button" onClick={() => setShowZeroStockNotice(false)} className="text-xs text-amber-800 hover:underline">
              Hide
            </button>
          </div>
        )}

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
                  <th className="p-3 text-left font-semibold text-neutral-700">Code</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Name</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Price</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Cost</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Category</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Stock</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Unit</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Tax</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Status</th>
                  <th className="p-3 text-left font-semibold text-neutral-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {displayedProductos.length === 0 && (
                  <tr>
                    <td colSpan={12} className="p-6 text-center text-neutral-500">
                      No products to show.
                    </td>
                  </tr>
                )}
                {displayedProductos.map((producto) => {
                  const isEditing = editingId === producto.id
                  const isSelected = selectedIds.has(producto.id)

                  return (
                    <tr
                      key={producto.id}
                      className={`hover:bg-neutral-50 ${isSelected ? 'bg-blue-50' : ''} ${
                        producto.errors.length > 0 ? 'bg-rose-50' : ''
                      }`}
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
                              const p = typeof producto.precio === 'string' ? parseFloat(producto.precio) : (producto.precio as number | null)
                              const v = typeof p === 'number' && !isNaN(p) ? p : parseFloat(String(producto.price || 0)) || 0
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
                            ${typeof producto.costo === 'number'
                              ? producto.costo.toFixed(2)
                              : (parseFloat(String(producto.costo || 0)) || 0).toFixed(2)}
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
                          <span className="text-neutral-700">{producto.categoria || '-'}</span>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <input
                            type="number"
                            value={editValues.stock ?? 0}
                            onChange={(e) => setEditValues({ ...editValues, stock: parseInt(e.target.value, 10) })}
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
                          <div className="text-xs text-rose-600 mt-1">{producto.errors.join(', ')}</div>
                        )}
                      </td>
                      <td className="p-3">
                        {isEditing ? (
                          <div className="flex gap-1">
                            <button
                              onClick={handleSaveEdit}
                              className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                            >
                              Save
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="px-2 py-1 border border-neutral-300 text-xs rounded hover:bg-neutral-50"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button onClick={() => handleEdit(producto)} className="px-2 py-1 text-blue-600 hover:underline text-xs">
                            Edit
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

        {displayedTotal > limit && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-neutral-600">
              Showing {offset + 1}-{Math.min(offset + limit, displayedTotal)} of {displayedTotal}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1.5 border border-neutral-300 rounded hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1.5 border border-neutral-300 rounded hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </ImportadorLayout>
  )
}

export default ProductosImportados
