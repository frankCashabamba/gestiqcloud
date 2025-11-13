// apps/tenant/src/modules/productos/List.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { listProductos, removeProducto, purgeProductos, bulkSetActive, bulkAssignCategory, type Producto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import CategoriasModal from './CategoriasModal'
import { useCurrency } from '../../hooks/useCurrency'

export default function ProductosList() {
  const [items, setItems] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { empresa } = useParams()
  const { success, error: toastError } = useToast()
  const { symbol: currencySymbol } = useCurrency()
  const [q, setQ] = useState('')
  const [filterActivo, setFilterActivo] = useState<'all' | 'activo' | 'inactivo'>('all')
  const [filterCategoria, setFilterCategoria] = useState<string>('all')
  const [showCategoriesModal, setShowCategoriesModal] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [categorias, setCategorias] = useState<Array<{ id: string; name: string }>>([])
  
  // Cargar categorías para el filtro
  useEffect(() => {
    ;(async () => {
      try {
        const { apiFetch } = await import('../../lib/http')
        const cats = await apiFetch<Array<{ id: string; name: string }>>('/api/v1/tenant/products/product-categories')
        setCategorias(Array.isArray(cats) ? cats : [])
      } catch (e) {
        console.error('Error cargando categorías:', e)
      }
    })()
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        setItems(await listProductos())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const [sortKey, setSortKey] = useState<'name' | 'sku' | 'price'>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(10)

  const filtered = useMemo(() => {
    let result = items.filter(
      (p) =>
        (p.name || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.sku || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.product_metadata?.Código_barras || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.product_metadata?.marca || '').toLowerCase().includes(q.toLowerCase())
    )

    if (filterActivo === 'activo') {
      result = result.filter((p) => p.active)
    } else if (filterActivo === 'inactivo') {
      result = result.filter((p) => !p.active)
    }

    if (filterCategoria !== 'all') {
      result = result.filter((p) => p.categoria === filterCategoria)
    }

    return result
  }, [items, q, filterActivo, filterCategoria])

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

  const exportCSV = () => {
    const headers = ['Código', 'Nombre', 'Precio', 'IVA', 'Estado']
    const rows = sorted.map((p) => [p.sku || '', p.name, p.price?.toFixed(2) || '0', `${p.iva_tasa || 0}%`, p.active ? 'Activo' : 'Inactivo'])

    const csv = [headers, ...rows].map((row) => row.join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `productos-${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Productos</h1>
          <p className="mt-1 text-sm text-gray-500">Catálogo de productos y servicios</p>
        </div>
        <div className="flex gap-2">
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={() => setShowCategoriesModal(true)}
            title="Gestionar categorías"
          >
            🏷️ categorías
          </button>
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={exportCSV}
            title="Exportar a CSV"
          >
            📥 Exportar
          </button>
                    {items.length > 0 && (<button
                      className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors font-medium"
                                  onClick={async () => {
                                    if (prompt('Para confirmar la eliminación de todos los productos, escriba PURGE') === 'PURGE') {
                                      try {
                                        await purgeProductos();
                                        setItems([]);
                                        success('Todos los productos han sido eliminados.');
                                      } catch (e) {
                                        toastError(getErrorMessage(e));
                                      }
                                    }
                                  }}                      title="Eliminar todos los productos"
                    >
                      🗑️ Eliminar todo
                    </button>)}
          
                    <button
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
            onClick={() => nav('nuevo')}
          >
            <span className="text-lg">➕</span> Nuevo producto
          </button>
        </div>
      </div>

      {/* Acciones masivas sobre productos SELECCIONADOS */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="font-medium text-blue-900">{selectedIds.length} producto(s) seleccionado(s)</span>
            <button
              onClick={() => setSelectedIds([])}
              className="text-sm text-blue-600 hover:underline"
            >
              Deseleccionar todos
            </button>
          </div>
          <div className="flex gap-2">
            <button
              className="bg-white border border-purple-300 text-purple-700 px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors font-medium text-sm"
              onClick={async () => {
                const categoryName = prompt('Nombre de la categoría para asignar:')
                if (!categoryName || !categoryName.trim()) return
                
                try {
                  const result = await bulkAssignCategory(selectedIds, categoryName.trim())
                  await (async () => {
                    setItems(await listProductos())
                  })()
                  setSelectedIds([])
                  success(`${result.updated} productos actualizados${result.category_created ? ' (categoría creada)' : ''}`)
                } catch (e: any) {
                  toastError(getErrorMessage(e))
                }
              }}
            >
              🏷️ Asignar categoría
            </button>
            <button
              className="bg-white border border-green-300 text-green-700 px-4 py-2 rounded-lg hover:bg-green-50 transition-colors font-medium text-sm"
              onClick={async () => {
                try {
                  await bulkSetActive(selectedIds, true)
                  await (async () => {
                    setItems(await listProductos())
                  })()
                  setSelectedIds([])
                  success('Productos activados')
                } catch (e: any) {
                  toastError(getErrorMessage(e))
                }
              }}
            >
              ✓ Activar
            </button>
            <button
              className="bg-white border border-yellow-300 text-yellow-700 px-4 py-2 rounded-lg hover:bg-yellow-50 transition-colors font-medium text-sm"
              onClick={async () => {
                try {
                  await bulkSetActive(selectedIds, false)
                  await (async () => {
                    setItems(await listProductos())
                  })()
                  setSelectedIds([])
                  success('Productos desactivados')
                } catch (e: any) {
                  toastError(getErrorMessage(e))
                }
              }}
            >
              ✗ Desactivar
            </button>
          </div>
        </div>
      )}

      <div className="bg-white shadow-sm rounded-lg p-4 mb-6 space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por nombre, Código, EAN o marca..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label="Buscar productos"
          />
          <select
            value={filterCategoria}
            onChange={(e) => setFilterCategoria(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">Todas las categorías</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={cat.name}>
                {cat.name}
              </option>
            ))}
          </select>
          <select
            value={filterActivo}
            onChange={(e) => setFilterActivo(e.target.value as any)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">Todos los estados</option>
            <option value="activo">Solo activos</option>
            <option value="inactivo">Solo inactivos</option>
          </select>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <label className="text-gray-600">Por página:</label>
            <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border border-gray-300 px-3 py-1 rounded">
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className="text-gray-600">
            <span className="font-medium">{filtered.length}</span> productos encontrados
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
                  <th className="px-4 py-3 text-center w-12">
                    <input
                      type="checkbox"
                      checked={view.length > 0 && selectedIds.length === view.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds(view.map(p => p.id))
                        } else {
                          setSelectedIds([])
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('sku')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Código {sortKey === 'sku' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('name')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Nombre {sortKey === 'name' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Categoría</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">EAN</th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('price')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Precio {sortKey === 'price' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">IVA</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Estado</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {view.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(p.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds([...selectedIds, p.id])
                        } else {
                          setSelectedIds(selectedIds.filter(id => id !== p.id))
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="font-mono text-xs text-gray-900 font-medium">{p.sku || '—'}</span>
                  </td>
                  <td className="px-4 py-3">
                  <div className="text-sm font-medium text-gray-900">{p.name}</div>
                  {p.description && <div className="text-xs text-gray-500 truncate max-w-xs">{p.description}</div>}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  {p.categoria ? (
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                          {p.categoria}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-gray-600">{p.product_metadata?.Código_barras || '—'}</span>
                    </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm font-semibold text-gray-900">{p.price?.toFixed(2) || '0.00'} {currencySymbol}</span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-600">{p.iva_tasa || 0}%</span>
                  </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          p.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {p.active ? '✓ Activo' : '✗ Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                      <Link to={`${p.id}/editar`} className="text-blue-600 hover:text-blue-900 mr-4">
                        Editar
                      </Link>
                      <button
                        className="text-amber-600 hover:text-amber-800 mr-4"
                        title="Crear receta desde este producto"
                        onClick={() => nav(`/${empresa || ''}/produccion/recetas/nueva?productId=${encodeURIComponent(p.id)}`)}
                      >
                        Crear receta
                      </button>
                      <button
                        className="text-red-600 hover:text-red-900"
                        onClick={async () => {
                          if (!confirm(`¿Eliminar "${p.name}"?`)) return
                          try {
                            await removeProducto(p.id)
                            setItems((prev) => prev.filter((x) => x.id !== p.id))
                            success('Producto eliminado')
                          } catch (e: any) {
                            toastError(getErrorMessage(e))
                          }
                        }}
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <div className="text-gray-400 text-4xl mb-3">📦</div>
                      <p className="text-gray-500 mb-2">No hay productos registrados</p>
                      <button className="text-blue-600 hover:underline font-medium" onClick={() => nav('nuevo')}>
                        Crear el primer producto
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

      {/* Modal de categorías */}
      {showCategoriesModal && (
        <CategoriasModal
          onClose={() => setShowCategoriesModal(false)}
          onCategoryCreated={() => {
            // Recargar productos para ver nuevas categorías
            setLoading(true)
            listProductos()
              .then((data) => setItems(data))
              .finally(() => setLoading(false))
          }}
        />
      )}
    </div>
  )
}
