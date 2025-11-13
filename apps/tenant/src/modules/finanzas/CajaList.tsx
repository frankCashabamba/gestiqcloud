import React, { useEffect, useMemo, useState } from 'react'
import { listCaja, createMovimientoCaja } from './services'
import type { Movimiento } from './types'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function CajaList() {
  const [items, setItems] = useState<Movimiento[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const { success, error } = useToast()

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')
  const [tipo, setTipo] = useState<'' | 'ingreso' | 'egreso'>('')
  const [per, setPer] = useState(25)

  const [form, setForm] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    concepto: '',
    tipo: 'ingreso' as 'ingreso' | 'egreso',
    monto: 0,
    referencia: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await listCaja()
      setItems(data)
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const filtered = useMemo(() => items.filter(m => {
    if (desde && m.fecha < desde) return false
    if (hasta && m.fecha > hasta) return false
    if (tipo && m.tipo !== tipo) return false
    if (q && !m.concepto.toLowerCase().includes(q.toLowerCase())) return false
    return true
  }), [items, desde, hasta, tipo, q])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(filtered, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const totalIngresos = filtered
    .filter(m => m.tipo === 'ingreso')
    .reduce((sum, m) => sum + m.monto, 0)
  
  const totalEgresos = filtered
    .filter(m => m.tipo === 'egreso')
    .reduce((sum, m) => sum + m.monto, 0)
  
  const saldo = totalIngresos - totalEgresos

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createMovimientoCaja(form)
      success('Movimiento creado')
      setShowForm(false)
      setForm({
        fecha: new Date().toISOString().slice(0, 10),
        concepto: '',
        tipo: 'ingreso',
        monto: 0,
        referencia: ''
      })
      loadData()
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  if (loading) return <div className="p-4 text-sm text-gray-500">Cargando…</div>

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-lg">Movimientos de Caja</h2>
        <button
          className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancelar' : '+ Nuevo Movimiento'}
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 border rounded p-4 mb-4">
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
            <div>
              <label className="block mb-1 text-sm font-medium">Fecha</label>
              <input
                type="date"
                value={form.fecha}
                onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                className="border px-2 py-1 rounded w-full"
                required
              />
            </div>
            <div>
              <label className="block mb-1 text-sm font-medium">Tipo</label>
              <select
                value={form.tipo}
                onChange={(e) => setForm({ ...form, tipo: e.target.value as any })}
                className="border px-2 py-1 rounded w-full"
                required
              >
                <option value="ingreso">Ingreso</option>
                <option value="egreso">Egreso</option>
              </select>
            </div>
            <div>
              <label className="block mb-1 text-sm font-medium">Concepto</label>
              <input
                type="text"
                value={form.concepto}
                onChange={(e) => setForm({ ...form, concepto: e.target.value })}
                className="border px-2 py-1 rounded w-full"
                required
              />
            </div>
            <div>
              <label className="block mb-1 text-sm font-medium">Monto</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={form.monto}
                onChange={(e) => setForm({ ...form, monto: Number(e.target.value) })}
                className="border px-2 py-1 rounded w-full"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block mb-1 text-sm font-medium">Referencia</label>
              <input
                type="text"
                value={form.referencia}
                onChange={(e) => setForm({ ...form, referencia: e.target.value })}
                className="border px-2 py-1 rounded w-full"
                placeholder="Opcional"
              />
            </div>
            <div className="col-span-2">
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Guardar Movimiento
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-green-50 border border-green-200 rounded p-3">
          <div className="text-sm text-gray-600">Total Ingresos</div>
          <div className="text-xl font-bold text-green-700">${totalIngresos.toFixed(2)}</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <div className="text-sm text-gray-600">Total Egresos</div>
          <div className="text-xl font-bold text-red-700">${totalEgresos.toFixed(2)}</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded p-3">
          <div className="text-sm text-gray-600">Saldo Neto</div>
          <div className={`text-xl font-bold ${saldo >= 0 ? 'text-blue-700' : 'text-red-700'}`}>
            ${saldo.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="mb-3 flex gap-3 items-end text-sm flex-wrap">
        <div>
          <label className="block mb-1">Tipo</label>
          <select
            value={tipo}
            onChange={(e) => setTipo(e.target.value as any)}
            className="border px-2 py-1 rounded"
          >
            <option value="">Todos</option>
            <option value="ingreso">Ingresos</option>
            <option value="egreso">Egresos</option>
          </select>
        </div>
        <div>
          <label className="block mb-1">Desde</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border px-2 py-1 rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Hasta</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border px-2 py-1 rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Buscar</label>
          <input
            placeholder="concepto"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border px-2 py-1 rounded"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>Por página</label>
        <select
          value={per}
          onChange={(e) => setPer(Number(e.target.value))}
          className="border px-2 py-1 rounded"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b bg-gray-50">
              <th className="py-2 px-3">Fecha</th>
              <th className="py-2 px-3">Concepto</th>
              <th className="py-2 px-3">Tipo</th>
              <th className="py-2 px-3 text-right">Monto</th>
              <th className="py-2 px-3">Referencia</th>
            </tr>
          </thead>
          <tbody>
            {view.map(m => (
              <tr key={m.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-3">{m.fecha}</td>
                <td className="py-2 px-3">{m.concepto}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    m.tipo === 'ingreso' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {m.tipo}
                  </span>
                </td>
                <td className={`py-2 px-3 text-right font-medium ${
                  m.tipo === 'ingreso' ? 'text-green-700' : 'text-red-700'
                }`}>
                  {m.tipo === 'ingreso' ? '+' : '-'}${m.monto.toFixed(2)}
                </td>
                <td className="py-2 px-3 text-gray-600">{m.referencia || '-'}</td>
              </tr>
            ))}
            {view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={5}>
                  Sin registros
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
