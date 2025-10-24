/**
 * Purchase List - Listado de compras
 */
import React, { useState, useEffect } from 'react'
import { listPurchases, getPurchaseStats, type Purchase, type PurchaseStats } from './services'

export default function PurchaseList() {
  const [purchases, setPurchases] = useState<Purchase[]>([])
  const [stats, setStats] = useState<PurchaseStats | null>(null)
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
        listPurchases(params),
        getPurchaseStats(params),
      ])
      setPurchases(data)
      setStats(statsData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value?: number) => {
    if (!value) return '-'
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Compras</h1>
        <p className="mt-1 text-sm text-slate-500">Registro de compras a proveedores</p>
      </div>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500">Total Compras</p>
            <p className="mt-3 text-3xl font-bold">{stats.total_compras}</p>
          </div>
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500">Cantidad Total</p>
            <p className="mt-3 text-3xl font-bold text-blue-600">{stats.total_cantidad.toFixed(2)}</p>
          </div>
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500">Costo Total</p>
            <p className="mt-3 text-3xl font-bold text-green-600">{formatCurrency(stats.total_costo)}</p>
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
            placeholder="Desde"
          />
          <input
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            className="block w-full rounded-lg border px-3 py-2"
            placeholder="Hasta"
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
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Proveedor</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Cantidad</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Costo Unit.</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {purchases.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm">{new Date(p.fecha).toLocaleDateString('es-ES')}</td>
                  <td className="px-6 py-4 text-sm font-medium">{p.supplier_name || '-'}</td>
                  <td className="px-6 py-4 text-right text-sm">{p.cantidad.toFixed(2)}</td>
                  <td className="px-6 py-4 text-right text-sm">{formatCurrency(p.costo_unitario)}</td>
                  <td className="px-6 py-4 text-right text-sm font-medium text-green-600">
                    {formatCurrency(p.total)}
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
