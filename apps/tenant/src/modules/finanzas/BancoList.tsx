import React, { useEffect, useMemo, useState } from 'react'
import { listBancos } from './services'
import type { Movimiento } from './types'

export default function BancoList() {
  const [items, setItems] = useState<Movimiento[]>([])
  const [loading, setLoading] = useState(true)
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => { listBancos().then((d)=> { setItems(d); setLoading(false) }) }, [])

  const filtered = useMemo(()=> items.filter(m => {
    if (desde && m.fecha < desde) return false
    if (hasta && m.fecha > hasta) return false
    if (q && !m.concepto.toLowerCase().includes(q.toLowerCase())) return false
    return true
  }), [items, desde, hasta, q])

  if (loading) return <div className="p-4 text-sm text-gray-500">Cargando…</div>

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-3">Movimientos Bancarios</h2>
      <div className="mb-3 flex gap-3 items-end text-sm">
        <div><label className="block mb-1">Desde</label><input type="date" value={desde} onChange={(e)=> setDesde(e.target.value)} className="border px-2 py-1 rounded" /></div>
        <div><label className="block mb-1">Hasta</label><input type="date" value={hasta} onChange={(e)=> setHasta(e.target.value)} className="border px-2 py-1 rounded" /></div>
        <div><label className="block mb-1">Buscar</label><input placeholder="concepto" value={q} onChange={(e)=> setQ(e.target.value)} className="border px-2 py-1 rounded" /></div>
      </div>
      <table className="min-w-full text-sm">
        <thead><tr className="text-left border-b"><th>Fecha</th><th>Concepto</th><th>Monto</th></tr></thead>
        <tbody>
          {filtered.map(m => (
            <tr key={m.id} className="border-b"><td>{m.fecha}</td><td>{m.concepto}</td><td>{m.monto.toFixed(2)}</td></tr>
          ))}
          {filtered.length===0 && (<tr><td className="py-3 px-3" colSpan={3}>Sin registros</td></tr>)}
        </tbody>
      </table>
    </div>
  )
}

