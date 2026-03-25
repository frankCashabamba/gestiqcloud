import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '@ui'
import { updateProducto, type Producto } from './productsApi'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { usePagination, Pagination } from '../../shared/pagination'
import { useCurrency } from '../../hooks/useCurrency'
import { apiFetch } from '../../lib/http'

export default function RawMaterialsList() {
  const { t } = useTranslation(['products', 'common'])
  const [items, setItems] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { empresa } = useParams()
  const { success, error: toastError } = useToast()
  const { symbol: currencySymbol } = useCurrency()
  const [q, setQ] = useState('')
  const [editingCostId, setEditingCostId] = useState<string | null>(null)
  const [editingCostValue, setEditingCostValue] = useState<string>('')
  const [editingStockId, setEditingStockId] = useState<string | null>(null)
  const [editingStockValue, setEditingStockValue] = useState<string>('')
  const [editingNameId, setEditingNameId] = useState<string | null>(null)
  const [editingNameValue, setEditingNameValue] = useState<string>('')

  const [sortKey, setSortKey] = useState<'name' | 'unit' | 'stock'>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(25)

  const loadRawMaterials = useCallback(async () => {
    try {
      setLoading(true)
      const data = await apiFetch<Producto[]>('/api/v1/tenant/products/raw-materials')
      setItems(data)
    } catch (e: any) {
      const m = getErrorMessage(e)
      setErrMsg(m)
      toastError(m)
    } finally {
      setLoading(false)
    }
  }, [toastError])

  useEffect(() => {
    void loadRawMaterials()
  }, [loadRawMaterials])

  const filtered = useMemo(() => {
    const ql = q.toLowerCase()
    return items.filter(
      (p) =>
        (p.name || '').toLowerCase().includes(ql) ||
        (p.sku || '').toLowerCase().includes(ql)
    )
  }, [items, q])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = ((a as any)[sortKey] || '').toString().toLowerCase()
      const bv = ((b as any)[sortKey] || '').toString().toLowerCase()
      return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, perPage, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('asc') }
  }

  const sortIcon = (key: string) =>
    sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''

  const saveCost = async (p: Producto, value: string) => {
    const newCost = parseFloat(value)
    if (!isNaN(newCost) && newCost >= 0) {
      try {
        await updateProducto(p.id, { cost_price: newCost })
        setItems((prev) => prev.map((x) => x.id === p.id ? { ...x, cost_price: newCost } : x))
      } catch (err: any) {
        toastError(getErrorMessage(err))
      }
    }
    setEditingCostId(null)
  }

  const saveStock = async (p: Producto, value: string) => {
    const newStock = parseFloat(value)
    if (!isNaN(newStock) && newStock >= 0) {
      try {
        await updateProducto(p.id, { stock: newStock })
        setItems((prev) => prev.map((x) => x.id === p.id ? { ...x, stock: newStock } : x))
        success(t('products:rawMaterials.stockUpdated', { name: p.name, defaultValue: `Stock de ${p.name} actualizado` }))
      } catch (err: any) {
        toastError(getErrorMessage(err))
      }
    }
    setEditingStockId(null)
  }

  const saveName = async (p: Producto, value: string) => {
    const newName = value.trim()
    if (newName && newName !== p.name) {
      try {
        await updateProducto(p.id, { name: newName } as any)
        setItems((prev) => prev.map((x) => x.id === p.id ? { ...x, name: newName } : x))
        success(t('products:rawMaterials.nameUpdated', { name: newName, defaultValue: `Nombre actualizado: ${newName}` }))
      } catch (err: any) {
        toastError(getErrorMessage(err))
      }
    }
    setEditingNameId(null)
  }

  return (
    <div className="p-6">
      <div style={{ marginBottom: '0.75rem' }}>
        <BackButton onClick={() => nav(-1)} />
      </div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🧂 {t('products:rawMaterials.title', 'Materias Primas')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('products:rawMaterials.subtitle', 'Insumos utilizados en recetas de producción')}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {filtered.length} {t('products:rawMaterials.count', 'insumo(s)')}
          </span>
        </div>
      </div>

      {errMsg && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-4">{errMsg}</div>
      )}

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('products:rawMaterials.search', 'Buscar materia prima...')}
          className="gc-input flex-1 min-w-[250px]"
        />
        <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="gc-input w-auto">
          {[10, 25, 50, 100].map((n) => (
            <option key={n} value={n}>{n} {t('products:perPage')}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">{t('common:loading', 'Cargando...')}</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th onClick={() => toggleSort('name')} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700">
                    {t('products:name')}{sortIcon('name')}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('products:code', 'SKU')}
                  </th>
                  <th onClick={() => toggleSort('unit')} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700">
                    {t('products:rawMaterials.unit', 'Unidad')}{sortIcon('unit')}
                  </th>
                  <th onClick={() => toggleSort('stock')} className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700">
                    {t('products:rawMaterials.stock', 'Stock')}{sortIcon('stock')}
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('products:rawMaterials.costPrice', 'Costo unitario')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('products:rawMaterials.rawOnly', 'Solo M.P.')}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {view.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      {editingNameId === p.id ? (
                        <input
                          type="text"
                          className="gc-input w-48 text-sm font-medium"
                          value={editingNameValue}
                          autoFocus
                          onChange={(e) => setEditingNameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveName(p, editingNameValue)
                            else if (e.key === 'Escape') setEditingNameId(null)
                          }}
                          onBlur={() => saveName(p, editingNameValue)}
                        />
                      ) : (
                        <span
                          className="text-sm font-medium text-gray-900 cursor-pointer hover:text-blue-600 hover:underline"
                          title="Click para editar nombre"
                          onClick={() => {
                            setEditingNameId(p.id)
                            setEditingNameValue(p.name)
                          }}
                        >
                          {p.name}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm text-gray-500">{p.sku || '—'}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        {p.unit || 'uds'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      {editingStockId === p.id ? (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          className="gc-input w-28 text-right text-sm"
                          value={editingStockValue}
                          autoFocus
                          onChange={(e) => setEditingStockValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveStock(p, editingStockValue)
                            else if (e.key === 'Escape') setEditingStockId(null)
                          }}
                          onBlur={() => saveStock(p, editingStockValue)}
                        />
                      ) : (
                        <span
                          className={`text-sm font-semibold cursor-pointer hover:text-blue-600 hover:underline ${p.stock <= 0 ? 'text-red-600' : 'text-gray-900'}`}
                          title="Click para editar stock"
                          onClick={() => {
                            setEditingStockId(p.id)
                            setEditingStockValue(String(p.stock ?? 0))
                          }}
                        >
                          {p.stock?.toFixed(2) || '0.00'} {p.unit || 'uds'}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      {editingCostId === p.id ? (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          className="gc-input w-24 text-right text-sm"
                          value={editingCostValue}
                          autoFocus
                          onChange={(e) => setEditingCostValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveCost(p, editingCostValue)
                            else if (e.key === 'Escape') setEditingCostId(null)
                          }}
                          onBlur={() => saveCost(p, editingCostValue)}
                        />
                      ) : (
                        <span
                          className="text-sm font-semibold text-gray-900 cursor-pointer hover:text-blue-600 hover:underline"
                          title="Click para editar costo"
                          onClick={() => {
                            setEditingCostId(p.id)
                            setEditingCostValue(String(p.cost_price ?? 0))
                          }}
                        >
                          {(p.cost_price ?? 0).toFixed(2)} {currencySymbol}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <label className="relative inline-flex items-center cursor-pointer" title={p.is_raw_material ? 'Solo materia prima (no aparece en productos ni inventario)' : 'Visible también en productos e inventario'}>
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={p.is_raw_material !== false}
                          onChange={async () => {
                            const newVal = !p.is_raw_material
                            try {
                              await updateProducto(p.id, { is_raw_material: newVal })
                              if (!newVal) {
                                setItems((prev) => prev.filter((x) => x.id !== p.id))
                                success(`${p.name} ahora es visible en productos e inventario`)
                              } else {
                                setItems((prev) => prev.map((x) => x.id === p.id ? { ...x, is_raw_material: newVal } : x))
                              }
                            } catch (err: any) {
                              toastError(getErrorMessage(err))
                            }
                          }}
                        />
                        <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-500"></div>
                      </label>
                    </td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center">
                      <div className="text-gray-400 text-4xl mb-3">🧂</div>
                      <p className="text-gray-500 mb-2">{t('products:rawMaterials.empty', 'No hay materias primas registradas')}</p>
                      <p className="text-gray-400 text-sm">{t('products:rawMaterials.emptyHint', 'Las materias primas se registran automáticamente al crear recetas')}</p>
                    </td>
                  </tr>
                )}
                {!loading && items.length > 0 && view.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center">
                      <p className="text-gray-500">{t('products:noResults')}</p>
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
