// apps/tenant/src/modules/inventory/StockList.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listStockItems, listWarehouses, createWarehouse, adjustStock, type StockItem, type Warehouse } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function StockList() {
  const [items, setItems] = useState<StockItem[]>([])
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { error: toastError } = useToast()

  const [q, setQ] = useState('')
  const [filterWarehouse, setFilterWarehouse] = useState<string | 'all'>('all')
  const [filterAlerta, setFilterAlerta] = useState<'all' | 'bajo' | 'sobre'>('all')
  const [sortKey, setSortKey] = useState<'producto' | 'qty' | 'warehouse'>('producto')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(25)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [stockData, warehousesData] = await Promise.all([
          listStockItems(),
          listWarehouses()
        ])
        setItems(stockData)
        setWarehouses(warehousesData)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const crearAlmacenDefecto = async () => {
    try {
      setLoading(true)
      const exists = warehouses.find(w => w.code === 'ALM-1')
      if (exists) return
      const w = await createWarehouse({ code: 'ALM-1', name: 'Principal', is_active: true })
      setWarehouses(prev => [...prev, w])
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const ajusteRapido = async () => {
    try {
      if (!warehouses.length) {
        await crearAlmacenDefecto()
      }
      const ws = warehouses.length ? warehouses : await listWarehouses()
      const wh = ws[0]
      if (!wh) {
        toastError('Crea primero un almacén')
        return
      }
      const productId = window.prompt('ID del producto (UUID)')?.trim()
      if (!productId) return
      const qtyStr = window.prompt('Cantidad a ajustar (ej. 10 o -5)')?.trim()
      if (!qtyStr) return
      const delta = Number(qtyStr)
      if (Number.isNaN(delta)) return
      await adjustStock({ warehouse_id: String(wh.id), product_id: productId, delta })
      const refreshed = await listStockItems()
      setItems(refreshed)
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const filtered = useMemo(() => {
    let result = items.filter((item) => {
      const matchesSearch =
        (item.product?.name || '').toLowerCase().includes(q.toLowerCase()) ||
        (item.product?.sku || '').toLowerCase().includes(q.toLowerCase())

      if (!matchesSearch) return false

      if (filterWarehouse !== 'all' && String(item.warehouse_id) !== String(filterWarehouse)) return false

      if (filterAlerta === 'bajo') {
        const min = item.product?.product_metadata?.reorder_point
        if (!min || item.qty > min) return false
      }

      if (filterAlerta === 'sobre') {
        const max = item.product?.product_metadata?.max_stock
        if (!max || item.qty <= max) return false
      }

      return true
    })

    return result
  }, [items, q, filterWarehouse, filterAlerta])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      if (sortKey === 'producto') {
        const av = (a.product?.name || '').toLowerCase()
        const bv = (b.product?.name || '').toLowerCase()
        return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
      }
      if (sortKey === 'qty') {
        return (a.qty - b.qty) * dir
      }
      if (sortKey === 'warehouse') {
        const av = (a.warehouse?.code || '').toLowerCase()
        const bv = (b.warehouse?.code || '').toLowerCase()
        return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
      }
      return 0
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, perPage, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const exportCSV = () => {
    const headers = ['Almacén', 'Code', 'Product', 'Stock', 'Ubicación', 'Lote', 'Caducidad']
    const rows = sorted.map((item) => [
      item.warehouse?.code || '',
      item.product?.sku || '',
      item.product?.name || '',
      item.qty.toString(),
      item.location || '',
      item.lot || '',
      item.expires_at || '',
    ])

    const csv = [headers, ...rows].map((row) => row.join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `stock-${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  const getAlertaInfo = (item: StockItem) => {
    const min = item.product?.product_metadata?.reorder_point
    const max = item.product?.product_metadata?.max_stock

    if (min && item.qty <= min) {
      return { tipo: 'bajo', texto: 'Stock bajo', color: 'bg-red-100 text-red-800' }
    }
    if (max && item.qty > max) {
      return { tipo: 'sobre', texto: 'Sobre-stock', color: 'bg-orange-100 text-orange-800' }
    }
    return null
  }

  const totalValue = useMemo(() => {
    return items.reduce((sum, item) => {
      const price = item.product?.price || 0
      return sum + (item.qty * price)
    }, 0)
  }, [items])

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Stock Actual</h1>
          <p className="mt-1 text-sm text-gray-500">
            Control de existencias por almacén
          </p>
          {defaultReorderPoint > 0 && (
            <p className="mt-1 text-xs text-gray-500">Minimo global de stock: {defaultReorderPoint}</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={exportCSV}
          >
            📥 Exportar CSV
          </button>          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={crearAlmacenDefecto}
            title="Crear almacén ALM-1"
          >
            Crear almacén
          </button>
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={ajusteRapido}
            title="Ajuste rápido de stock"
          >
            Ajuste rápido
          </button>
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            onClick={() => nav('/inventory/movimientos/nuevo')}
          >
            ➕ Nuevo movimiento
          </button>
        </div>
      </div>

      {/* KPIs Rápidos */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">Total productos</div>
          <div className="text-2xl font-bold text-gray-900">{items.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">Valor total stock</div>
          <div className="text-2xl font-bold text-green-600">${totalValue.toFixed(2)}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">Alertas stock bajo</div>
          <div className="text-2xl font-bold text-red-600">
            {items.filter(i => {
              const reorderPoint = i.product?.product_metadata?.reorder_point
              return reorderPoint && i.qty <= reorderPoint
            }).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">Sobre-stock</div>
          <div className="text-2xl font-bold text-orange-600">
            {items.filter(i => {
              const maxStock = i.product?.product_metadata?.max_stock
              return maxStock && i.qty > maxStock
            }).length}
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white shadow-sm rounded-lg p-4 mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por nombre o código..."
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label="Buscar productos"
          />

          <select
            value={filterWarehouse}
            onChange={(e) => setFilterWarehouse(e.target.value === 'all' ? 'all' : String(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todos los almacenes</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} ({w.code})
              </option>
            ))}
          </select>

          <select
            value={filterAlerta}
            onChange={(e) => setFilterAlerta(e.target.value as any)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todas las alertas</option>
            <option value="bajo">Solo stock bajo</option>
            <option value="sobre">Solo sobre-stock</option>
          </select>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <label className="text-gray-600">Por página:</label>
            <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border border-gray-300 px-3 py-1 rounded">
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className="text-gray-600">
            <span className="font-medium">{filtered.length}</span> productos en stock
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <svg className="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      )}

      {errMsg && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <strong className="font-medium">Error:</strong> {errMsg}
        </div>
      )}

      {!loading && (
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      onClick={() => {
                        setSortKey('warehouse')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Almacén {sortKey === 'warehouse' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Código</th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      onClick={() => {
                        setSortKey('producto')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Producto {sortKey === 'producto' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-right">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      onClick={() => {
                        setSortKey('qty')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Stock {sortKey === 'qty' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Ubicación</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Lote</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Caducidad</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Estado</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {view.map((item) => {
                  const alerta = getAlertaInfo(item)
                  return (
                    <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-sm font-medium text-gray-900">{item.warehouse?.code || '—'}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-mono text-xs text-gray-600">{item.product?.sku || '—'}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-gray-900">{item.product?.name || '—'}</div>
                        {item.product?.product_metadata?.reorder_point && (
                          <div className="text-xs text-gray-500">
                            Min stock: {item.product.product_metadata.reorder_point} {item.product.product_metadata.max_stock && `/ Max: ${item.product.product_metadata.max_stock}`}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <span className={`text-lg font-bold ${item.qty < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                          {item.qty.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{item.location || '—'}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {item.lot && <span className="font-mono text-xs text-gray-600">{item.lot}</span>}
                        {!item.lot && <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {item.expires_at ? new Date(item.expires_at).toLocaleDateString('es') : '—'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {alerta ? (
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${alerta.color}`}>
                            {alerta.tipo === 'bajo' ? '⚠️' : '📊'} {alerta.texto}
                          </span>
                        ) : (
                          <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                            ✓ OK
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <div className="text-gray-400 text-4xl mb-3">📦</div>
                      <p className="text-gray-500 mb-2">No hay stock registrado</p>
                      <button
                        className="text-blue-600 hover:underline font-medium"
                        onClick={() => nav('/inventory/movimientos/nuevo')}
                      >
                        Crear primer movimiento
                      </button>
                    </td>
                  </tr>
                )}
                {!loading && items.length > 0 && view.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <p className="text-gray-500">No se encontraron productos con esos filtros</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-gray-200">
              <Pagination page={page} setPage={setPage} totalPages={totalPages} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
