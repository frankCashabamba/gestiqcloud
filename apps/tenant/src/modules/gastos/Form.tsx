/**
 * Gasto Form
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createGasto } from './services'

export default function GastoForm() {
  const navigate = useNavigate()
  const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0])
  const [concepto, setConcepto] = useState('')
  const [importe, setImporte] = useState('')
  const [categoria, setCategoria] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      await createGasto({ fecha, concepto, monto: parseFloat(importe), proveedor_id: undefined })
      alert('Gasto registrado')
      navigate('/gastos')
    } catch (err: any) {
      alert(err.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Nuevo Gasto</h1>
      <form onSubmit={handleSubmit} className="rounded-xl border bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">Fecha *</label>
              <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2" required />
            </div>
            <div>
              <label className="block text-sm font-medium">Categoría</label>
              <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2">
                <option value="">Seleccionar...</option>
                <option value="suministros">Suministros</option>
                <option value="servicios">Servicios</option>
                <option value="alquiler">Alquiler</option>
                <option value="otros">Otros</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium">Concepto *</label>
            <input type="text" value={concepto} onChange={(e) => setConcepto(e.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium">Importe (€) *</label>
            <input type="number" step="0.01" value={importe} onChange={(e) => setImporte(e.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2" required />
          </div>
          <div className="flex gap-3">
            <button type="submit" disabled={loading} className="flex-1 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300">
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
            <button type="button" onClick={() => navigate('/gastos')} className="rounded-lg border px-6 py-3 font-medium hover:bg-slate-50">
              Cancelar
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
