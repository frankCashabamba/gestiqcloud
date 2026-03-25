// apps/tenant/src/modules/inventario/StockListFixed.tsx (UTF-8)
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  listStockItems,
  listWarehouses,
  createWarehouse,
  adjustStock,
  syncFromProducts,
  type StockItem,
  type Warehouse,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { getDefaultReorderPoint, getCompanySettings } from '../../services/companySettings'
import { isStandardUnitCode } from '../../services/unitService'

type QuickAdjustState = {
  open: boolean
  productId: string
  productLabel: string
  productSearch: string
  dropdownOpen: boolean
  delta: string
}

export default function StockList() {
  const { t } = useTranslation(['inventory', 'common'])
  const [items, setItems] = useState<StockItem[]>([])
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { error: toastError, info, success } = useToast()

  const [q, setQ] = useState('')
  const [filterWarehouse, setFilterWarehouse] = useState<string | 'all'>('all')
  const [filterAlerta, setFilterAlerta] = useState<'all' | 'bajo' | 'sobre'>('all')
  const [sortKey, setSortKey] = useState<'producto' | 'qty' | 'warehouse'>('producto')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(25)
  const [defaultReorderPoint, setDefaultReorderPoint] = useState(0)
  const [showZeroStock, setShowZeroStock] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [quickAdjust, setQuickAdjust] = useState<QuickAdjustState>({
    open: false, productId: '', productLabel: '', productSearch: '', dropdownOpen: false, delta: '',
  })
  const [quickAdjusting, setQuickAdjusting] = useState(false)
  const quickProductInputRef = useRef<HTMLInputElement>(null)

  // Productos únicos derivados de los items cargados (sin duplicados por almacén)
  const uniqueProducts = useMemo(() => {
    const seen = new Set<string>()
    return items
      .filter((i) => { const k = String(i.product_id); if (seen.has(k)) return false; seen.add(k); return true })
      .map((i) => ({ id: String(i.product_id), name: i.product?.name ?? '—', sku: i.product?.sku ?? '' }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [items])

  const filteredQuickProducts = useMemo(() => {
    const q = quickAdjust.productSearch.toLowerCase()
    return uniqueProducts.filter(
      (p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q),
    ).slice(0, 30)
  }, [uniqueProducts, quickAdjust.productSearch])

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const settings = await getCompanySettings()
        setDefaultReorderPoint(getDefaultReorderPoint(settings))
        const [stockData, warehousesData] = await Promise.all([
          listStockItems(),
          listWarehouses(),
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

  const getReorderPoint = (item: StockItem) => {
    const productPoint = item.product?.product_metadata?.reorder_point
    const point = productPoint ?? defaultReorderPoint
    const num = Number(point)
    return Number.isFinite(num) ? num : 0
  }

  const crearAlmacenDefecto = async () => {
    try {
      setLoading(true)
      const exists = warehouses.find((w) => w.code === 'ALM-1')
      if (exists) {
        info(t('inventory:stock.warehouseExists'))
        return
      }
      const w = await createWarehouse({ code: 'ALM-1', name: 'Principal', is_active: true })
      setWarehouses((prev) => [...prev, w])
      success(t('inventory:stock.warehouseCreated'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const EMPTY_QUICK: QuickAdjustState = {
    open: false, productId: '', productLabel: '', productSearch: '', dropdownOpen: false, delta: '',
  }

  const openQuickAdjust = async () => {
    if (!warehouses.length) await crearAlmacenDefecto()
    setQuickAdjust({ ...EMPTY_QUICK, open: true })
    setTimeout(() => quickProductInputRef.current?.focus(), 50)
  }

  const submitQuickAdjust = async () => {
    const delta = Number(quickAdjust.delta)
    if (!quickAdjust.productId) { toastError(t('inventory:quickAdjust.productPrompt')); return }
    if (!quickAdjust.delta.trim() || Number.isNaN(delta)) { toastError(t('inventory:quickAdjust.qtyPrompt')); return }
    const ws = warehouses.length ? warehouses : await listWarehouses()
    const wh = ws[0]
    if (!wh) { toastError(t('inventory:quickAdjust.missingWarehouse')); return }
    try {
      setQuickAdjusting(true)
      await adjustStock({ warehouse_id: String(wh.id), product_id: quickAdjust.productId, delta })
      const refreshed = await listStockItems()
      setItems(refreshed)
      setQuickAdjust(EMPTY_QUICK)
      success(t('inventory:quickAdjust.success', { delta, productId: quickAdjust.productLabel || quickAdjust.productId }))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setQuickAdjusting(false)
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      const res = await syncFromProducts()
      success(t('inventory:stock.syncSuccess', { created: res.created, updated: res.updated, warehouse: res.warehouse }))
      const refreshed = await listStockItems()
      setItems(refreshed)
    } catch (e: any) {
      const msg = getErrorMessage(e)
      if (msg.includes('almacén') || msg.includes('warehouse')) {
        toastError(t('inventory:stock.syncNoWarehouse'))
      } else {
        toastError(msg)
      }
    } finally {
      setSyncing(false)
    }
  }

  const filtered = useMemo(() => {
    const ql = q.toLowerCase()
    return items.filter((item) => {
      if (!showZeroStock && item.qty <= 0) return false
      if (item.product?.is_raw_material) return false

      const matchesSearch =
        (item.product?.name || '').toLowerCase().includes(ql) ||
        (item.product?.sku || '').toLowerCase().includes(ql)

      if (!matchesSearch) return false

      if (filterWarehouse !== 'all' && String(item.warehouse_id) !== String(filterWarehouse)) return false

      if (filterAlerta === 'bajo') {
        const min = getReorderPoint(item)
        if (min <= 0 || item.qty > min) return false
      }

      if (filterAlerta === 'sobre') {
        const max = item.product?.product_metadata?.max_stock
        if (!max || item.qty <= max) return false
      }

      return true
    })
  }, [items, q, filterWarehouse, filterAlerta, defaultReorderPoint, showZeroStock])

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

  const exportCSV = () => {
    const headers = [t('inventory:stock.warehouse'), 'SKU', t('inventory:stock.product'), t('inventory:stock.stock'), t('inventory:stock.location'), t('inventory:stock.batch'), t('inventory:stock.expiry')]
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
    const min = getReorderPoint(item)
    const max = item.product?.product_metadata?.max_stock
    if (min > 0 && item.qty <= min) return { tipo: 'bajo' as const, texto: t('inventory:stock.lowStock'), color: 'bg-red-100 text-red-800' }
    if (max && item.qty > max) return { tipo: 'sobre' as const, texto: t('inventory:stock.overstock'), color: 'bg-orange-100 text-orange-800' }
    return null
  }

  const totalValue = useMemo(() => {
    return items.reduce((sum, item) => {
      const precio = Number(item.product?.price ?? 0) || 0
      const qty = Number(item.qty ?? 0) || 0
      return sum + qty * precio
    }, 0)
  }, [items])

  const totalProductosUnicos = useMemo(() => {
    const set = new Set(items.filter(i => i.qty > 0).map((i) => String(i.product_id)))
    return set.size
  }, [items])

  const totalProductosConStock0 = useMemo(() => {
    const set = new Set(items.filter(i => i.qty <= 0).map((i) => String(i.product_id)))
    return set.size
  }, [items])

  return (
    <>
    {quickAdjust.open && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setQuickAdjust(EMPTY_QUICK)}>
        <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t('inventory:stock.quickAdjust')}</h3>
          <div className="space-y-4">

            {/* Combobox producto */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Producto</label>
              <div className="relative">
                <input
                  ref={quickProductInputRef}
                  type="text"
                  value={quickAdjust.dropdownOpen ? quickAdjust.productSearch : (quickAdjust.productLabel || quickAdjust.productSearch)}
                  onChange={(e) => setQuickAdjust((s) => ({ ...s, productSearch: e.target.value, dropdownOpen: true, productId: '', productLabel: '' }))}
                  onFocus={() => setQuickAdjust((s) => ({ ...s, productSearch: '', dropdownOpen: true }))}
                  onBlur={() => setTimeout(() => setQuickAdjust((s) => ({ ...s, dropdownOpen: false })), 150)}
                  placeholder="Buscar por nombre o SKU…"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm pr-7"
                  autoComplete="off"
                />
                {quickAdjust.productId && (
                  <button
                    type="button"
                    onClick={() => setQuickAdjust((s) => ({ ...s, productId: '', productLabel: '', productSearch: '' }))}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
                  >×</button>
                )}
                {quickAdjust.dropdownOpen && (
                  <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    {filteredQuickProducts.length === 0 ? (
                      <div className="px-3 py-2 text-sm text-gray-400">Sin resultados</div>
                    ) : filteredQuickProducts.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onMouseDown={() => setQuickAdjust((s) => ({
                          ...s,
                          productId: p.id,
                          productLabel: p.name,
                          productSearch: '',
                          dropdownOpen: false,
                        }))}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center gap-2"
                      >
                        {p.sku && <span className="font-mono text-xs text-gray-400 shrink-0">{p.sku}</span>}
                        <span className="text-gray-800 truncate">{p.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Delta */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('inventory:quickAdjust.qtyPrompt')}
              </label>
              <input
                type="number"
                step="any"
                value={quickAdjust.delta}
                onChange={(e) => setQuickAdjust((s) => ({ ...s, delta: e.target.value }))}
                onKeyDown={(e) => e.key === 'Enter' && submitQuickAdjust()}
                placeholder="Ej: 10 (entrada) o -5 (salida)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={submitQuickAdjust}
              disabled={quickAdjusting || !quickAdjust.productId}
              className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm disabled:opacity-50"
            >
              {quickAdjusting ? t('common:saving') : t('common:confirm')}
            </button>
            <button
              onClick={() => setQuickAdjust(EMPTY_QUICK)}
              className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg hover:bg-gray-200 transition-colors font-medium text-sm"
            >
              {t('common:cancel')}
            </button>
          </div>
        </div>
      </div>
    )}
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('inventory:stock.title')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('inventory:stock.subtitle')}</p>
          {defaultReorderPoint > 0 && (
            <p className="mt-1 text-xs text-gray-500">{t('inventory:stock.globalMin')}: {defaultReorderPoint}</p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            className="bg-yellow-500 text-white px-4 py-2 rounded-lg hover:bg-yellow-600 transition-colors font-medium disabled:opacity-50"
            onClick={handleSync}
            disabled={syncing}
            title="Sincronizar stock desde productos"
          >
            🔄 {syncing ? t('inventory:stock.syncing') : t('inventory:stock.syncFromProducts')}
          </button>
          <button className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium" onClick={exportCSV}>
            {t('inventory:stock.exportCsv')}
          </button>
          <button className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium" onClick={crearAlmacenDefecto} title="Create warehouse ALM-1">
            {t('inventory:stock.createWarehouse')}
          </button>
          <button className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium" onClick={openQuickAdjust} title="Quick adjust de stock">
            {t('inventory:stock.quickAdjust')}
          </button>
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium" onClick={() => nav('movimientos/nuevo')}>
            {t('inventory:stock.newMovement')}
          </button>
        </div>
      </div>

      {/* KPIs rápidos */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">{t('inventory:stock.totalProducts')}</div>
          <div className="text-2xl font-bold text-gray-900">{totalProductosUnicos}</div>
          {totalProductosConStock0 > 0 && (
            <div className="text-xs text-red-500 mt-1">+{totalProductosConStock0} sin stock</div>
          )}
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">{t('inventory:stock.totalStockValue')}</div>
          <div className="text-2xl font-bold text-green-600">${totalValue.toFixed(2)}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">{t('inventory:stock.lowStockAlerts')}</div>
          <div className="text-2xl font-bold text-red-600">
            {items.filter((i) => {
              const min = getReorderPoint(i)
              return min > 0 && i.qty <= min
            }).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="text-sm text-gray-600">{t('inventory:stock.overstock')}</div>
          <div className="text-2xl font-bold text-orange-600">{items.filter((i) => i.product?.product_metadata?.max_stock && i.qty > i.product.product_metadata.max_stock).length}</div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white shadow-sm rounded-lg p-4 mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t('inventory:stock.searchPlaceholder')}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label={t('inventory:stock.searchAriaLabel')}
          />
          <select
            value={filterWarehouse}
            onChange={(e) => setFilterWarehouse(e.target.value === 'all' ? 'all' : String(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">{t('inventory:stock.allWarehouses')}</option>
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
            <option value="all">{t('inventory:stock.allAlerts')}</option>
            <option value="bajo">{t('inventory:stock.lowStockOnly')}</option>
            <option value="sobre">{t('inventory:stock.overstockOnly')}</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showZeroStock}
            onChange={(e) => setShowZeroStock(e.target.checked)}
            className="rounded"
          />
          Mostrar productos sin stock (qty ≤ 0)
        </label>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-600 mb-4">
          <span>{t('inventory:stock.loading')}</span>
          <svg className="animate-spin h-4 w-4 text-gray-500" viewBox="0 0 24 24">
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
                      {t('inventory:stock.warehouse')} {sortKey === 'warehouse' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('inventory:stock.code')}</th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      onClick={() => {
                        setSortKey('producto')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      {t('inventory:stock.product')} {sortKey === 'producto' && (sortDir === 'asc' ? '▲' : '▼')}
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
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('inventory:stock.location')}</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('inventory:stock.batch')}</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('inventory:stock.expiry')}</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('inventory:stock.status')}</th>
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
                        {getReorderPoint(item) > 0 && (
                          <div className="text-xs text-gray-500">
                            {t('inventory:stock.minStock')}: {getReorderPoint(item)}
                            {item.product?.product_metadata?.max_stock ? ` / ${t('inventory:stock.maxStock')}: ${item.product.product_metadata?.max_stock}` : ''}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <span className={`text-lg font-bold ${item.qty <= 0 ? 'text-red-600' : 'text-gray-900'}`}>
                          {item.qty.toFixed(2)}
                          {item.unit && item.unit !== 'unit' && (
                            <span className="ml-1 text-sm font-normal text-gray-500">{item.unit}</span>
                          )}
                        </span>
                        {(() => {
                          const stockUnit = item.unit ?? ''
                          const pu = item.pack_unit ?? ''
                          const showEquiv = item.pack_size && item.pack_size > 0 && pu
                            && isStandardUnitCode(pu)
                            && !isStandardUnitCode(stockUnit)
                          if (!showEquiv) return null
                          return (
                            <div className="text-xs text-gray-400 mt-0.5">
                              = {(item.qty * item.pack_size!).toFixed(0)} {pu}
                            </div>
                          )
                        })()}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{item.location || '—'}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {item.lot ? (
                          <span className="font-mono text-xs text-gray-600">{item.lot}</span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {item.expires_at ? new Date(item.expires_at).toLocaleDateString('es') : '—'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {alerta ? (
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${alerta.color}`}>
                            {alerta.texto}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-500">OK</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
            <Pagination page={page} totalPages={totalPages} onPageChange={(p) => setPage(p)} />
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>{t('inventory:stock.perPage')}:</span>
              <select value={perPage} onChange={(e) => setPerPage(Number(e.target.value))} className="border border-gray-300 rounded px-2 py-1">
                {[10, 25, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  )
}
