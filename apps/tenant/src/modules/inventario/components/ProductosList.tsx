import React, { useEffect, useState } from 'react'
import { fetchProductos } from '../services/inventario'
import { ensureArray } from '../../../shared/utils/array'
import type { Producto } from '../types/producto'
import { usePagination, Pagination } from '../../../shared/pagination'

export function ProductosList() {
  const [items, setItems] = useState<Producto[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => {
    fetchProductos().then((d)=> {
      setItems(ensureArray<Producto>(d))
      setLoading(false)
    })
  }, [])
  const base = Array.isArray(items) ? items : []
  const filtered = base.filter(p => (p.nombre||'').toLowerCase().includes(q.toLowerCase()) || (p.sku||'').toLowerCase().includes(q.toLowerCase()))
  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  return (
    <div className="p-4">
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      <h2 className="font-semibold text-lg mb-4">Productos</h2>
      <input value={q} onChange={(e)=> setQ(e.target.value)} placeholder="Buscar nombre o SKU..." className="mb-3 w-full px-3 py-2 border rounded text-sm" />
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b"><th>SKU</th><th>Nombre</th><th>Stock</th><th>Precio</th></tr>
        </thead>
        <tbody>
          {view.map(p => (
            <tr key={p.id} className="border-b">
              <td>{p.sku}</td>
              <td>{p.nombre}</td>
              <td>{p.stock}</td>
              <td>{p.precio.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
