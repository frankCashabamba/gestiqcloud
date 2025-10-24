/**
 * Milk Record List - Listado de registros de leche
 */
import React, { useState, useEffect } from 'react'
import { listMilkRecords, getMilkStats, type MilkRecord, type MilkStats } from './services'

export default function MilkRecordList() {
  const [records, setRecords] = useState<MilkRecord[]>([])
  const [stats, setStats] = useState<MilkStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  useEffect(() => {
    loadData()
  }, [fechaDesde, fechaHasta])

  const loadData = async () => {
    try {
      setLoading(true)
      const params = {
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
      }
      const [data, statsData] = await Promise.all([
        listMilkRecords(params),
        getMilkStats(params),
      ])
      setRecords(data)
      setStats(statsData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Registro de Leche</h1>
        <p className="mt-1 text-sm text-slate-500">Control diario de recepción de leche</p>
      </div>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500">Total Registros</p>
            <p className="mt-3 text-3xl font-bold">{stats.total_registros}</p>
          </div>
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500">Total Litros</p>
            <p className="mt-3 text-3xl font-bold text-purple-600">{stats.total_litros.toFixed(0)} L</p>
          </div>
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500">Promedio Grasa</p>
            <p className="mt-3 text-3xl font-bold text-amber-600">
              {stats.promedio_grasa ? `${stats.promedio_grasa.toFixed(1)}%` : '-'}
            </p>
          </div>
        </div>
      )}

      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-3">
          <input
            type="date"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
            className="block w-full rounded-lg border px-3 py-2"
          />
          <input
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            className="block w-full rounded-lg border px-3 py-2"
          />
          <button
            onClick={() => {
              setFechaDesde('')
              setFechaHasta('')
            }}
            className="rounded-lg border px-4 py-2 hover:bg-slate-50"
          >
            Limpiar
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full">
            <thead className="border-b bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Fecha</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Litros</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">% Grasa</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Notas</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {records.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm">{new Date(r.fecha).toLocaleDateString('es-ES')}</td>
                  <td className="px-6 py-4 text-right text-sm font-medium text-purple-600">
                    {r.litros.toFixed(2)} L
                  </td>
                  <td className="px-6 py-4 text-right text-sm">
                    {r.grasa_pct ? `${r.grasa_pct.toFixed(1)}%` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">{r.notas || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
