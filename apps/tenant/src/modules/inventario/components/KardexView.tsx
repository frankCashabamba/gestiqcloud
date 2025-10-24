import React, { useEffect, useState } from 'react'
import { fetchKardex } from '../services/inventario'
import { ensureArray } from '../../../shared/utils/array'
import type { KardexEntry } from '../types/producto'
import { usePagination, Pagination } from '../../../shared/pagination'

export function KardexView() {
  const [items, setItems] = useState<KardexEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  useEffect(() => {
    fetchKardex().then((d)=> {
      setItems(ensureArray<KardexEntry>(d))
      setLoading(false)
    })
  }, [])
  const base = Array.isArray(items) ? items : []
  const filtered = base.filter(k => (!from || k.fecha >= from) && (!to || k.fecha <= to))
  const { page, setPage, totalPages, view } = usePagination(filtered, 15)

  return (
    <div className="p-4">
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      <h2 className="font-semibold text-lg mb-4">Kardex</h2>
      <div className="flex gap-2 mb-3 text-sm">
        <div>
          <label className="block mb-1">Desde</label>
          <input type="date" value={from} onChange={(e)=> setFrom(e.target.value)} className="border px-2 py-1 rounded" />
        </div>
        <div>
          <label className="block mb-1">Hasta</label>
          <input type="date" value={to} onChange={(e)=> setTo(e.target.value)} className="border px-2 py-1 rounded" />
        </div>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b"><th>Fecha</th><th>Movimiento</th><th>Cantidad</th><th>Saldo</th><th>Referencia</th></tr>
        </thead>
        <tbody>
          {view.map(k => (
            <tr key={k.id} className="border-b">
              <td>{k.fecha}</td>
              <td>{k.movimiento}</td>
              <td>{k.cantidad}</td>
              <td>{k.saldo}</td>
              <td>{k.referencia || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
