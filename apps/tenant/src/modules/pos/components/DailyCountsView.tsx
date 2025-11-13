/** DailyCountsView - Vista de reportes diarios de caja */
import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listDailyCounts, listRegisters } from '../services'

interface DailyCount {
  id: string
  register_id: string
  shift_id: string
  count_date: string
  opening_float: number
  cash_sales: number
  card_sales: number
  other_sales: number
  total_sales: number
  expected_cash: number
  counted_cash: number
  discrepancy: number
  loss_amount: number
  loss_note?: string
  created_at: string
}

interface Register {
  id: string
  name: string
}

export default function DailyCountsView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const registerId = searchParams.get('register_id') || undefined
  const [counts, setCounts] = useState<DailyCount[]>([])
  const [registers, setRegisters] = useState<Register[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [registerId])

  const loadData = async () => {
    try {
      setLoading(true)
      // Cargar cajas disponibles
      const regs = await listRegisters()
      setRegisters(regs.filter((r: any) => r.active))

      // Cargar reportes diarios
      const params: any = { limit: 50 }
      if (registerId) params.register_id = registerId
      const data = await listDailyCounts(params)
      setCounts(data)
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const handleRegisterChange = (newRegisterId: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (newRegisterId) {
      newParams.set('register_id', newRegisterId)
    } else {
      newParams.delete('register_id')
    }
    setSearchParams(newParams)
  }

  if (loading) {
    return <div className="p-4 text-center">Cargando reportes diarios...</div>
  }

  if (error) {
    return <div className="p-4 text-center text-red-600">Error: {error}</div>
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Reportes Diarios de Caja</h2>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium">Filtrar por caja:</label>
          <select
            value={registerId || ''}
            onChange={(e) => handleRegisterChange(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="">Todas las cajas</option>
            {registers.map((reg) => (
              <option key={reg.id} value={reg.id}>
                {reg.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {counts.length === 0 ? (
        <p className="text-gray-500">No hay reportes diarios disponibles.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 p-2 text-left">Fecha</th>
                <th className="border border-gray-300 p-2 text-right">Fondo Inicial</th>
                <th className="border border-gray-300 p-2 text-right">Ventas Efectivo</th>
                <th className="border border-gray-300 p-2 text-right">Ventas Totales</th>
                <th className="border border-gray-300 p-2 text-right">Esperado</th>
                <th className="border border-gray-300 p-2 text-right">Contado</th>
                <th className="border border-gray-300 p-2 text-right">Diferencia</th>
                <th className="border border-gray-300 p-2 text-left">Notas</th>
              </tr>
            </thead>
            <tbody>
              {counts.map((count) => (
                <tr key={count.id} className="hover:bg-gray-50">
                  <td className="border border-gray-300 p-2">
                    {new Date(count.count_date).toLocaleDateString()}
                  </td>
                  <td className="border border-gray-300 p-2 text-right">
                    €{count.opening_float.toFixed(2)}
                  </td>
                  <td className="border border-gray-300 p-2 text-right">
                    €{count.cash_sales.toFixed(2)}
                  </td>
                  <td className="border border-gray-300 p-2 text-right">
                    €{count.total_sales.toFixed(2)}
                  </td>
                  <td className="border border-gray-300 p-2 text-right">
                    €{count.expected_cash.toFixed(2)}
                  </td>
                  <td className="border border-gray-300 p-2 text-right">
                    €{count.counted_cash.toFixed(2)}
                  </td>
                  <td className={`border border-gray-300 p-2 text-right ${
                    count.discrepancy !== 0 ? 'text-red-600 font-semibold' : ''
                  }`}>
                    €{count.discrepancy.toFixed(2)}
                  </td>
                  <td className="border border-gray-300 p-2">
                    {count.loss_note || (count.loss_amount > 0 ? `Pérdida: €${count.loss_amount.toFixed(2)}` : '-')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
