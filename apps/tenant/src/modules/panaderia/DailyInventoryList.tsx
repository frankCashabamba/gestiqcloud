/**
 * Daily Inventory List - Listado de inventario diario
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listDailyInventory, getDailyInventoryStats, type DailyInventory, type InventoryStats } from './services'

export default function DailyInventoryList() {
  const [inventory, setInventory] = useState<DailyInventory[]>([])
  const [stats, setStats] = useState<InventoryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Filtros
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  useEffect(() => {
    loadData()
  }, [fechaDesde, fechaHasta])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const params = {
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
      }
      
      const [inventoryData, statsData] = await Promise.all([
        listDailyInventory(params),
        getDailyInventoryStats(params),
      ])
      
      setInventory(inventoryData)
      setStats(statsData)
    } catch (err: any) {
      setError(err.message || 'Error al cargar inventario')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value?: number) => {
    if (value === null || value === undefined) return '-'
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(value)
  }

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Inventario Diario</h1>
          <p className="mt-1 text-sm text-slate-500">
            Control de stock inicial, ventas y sobrante por producto y día
          </p>
        </div>
        <Link
          to="nuevo"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-500"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Registro
        </Link>
      </div>

      {/* KPIs */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Registros</p>
            <p className="mt-3 text-3xl font-bold text-slate-900">{stats.total_registros}</p>
          </div>
          
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Unidades Vendidas</p>
            <p className="mt-3 text-3xl font-bold text-blue-600">{formatNumber(stats.total_ventas_unidades)}</p>
          </div>
          
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Ingresos Totales</p>
            <p className="mt-3 text-3xl font-bold text-green-600">{formatCurrency(stats.total_ingresos)}</p>
          </div>
          
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Con Ajuste</p>
            <p className="mt-3 text-3xl font-bold text-amber-600">{stats.registros_con_ajuste}</p>
            <p className="mt-1 text-xs text-slate-400">
              {stats.total_registros > 0 
                ? `${((stats.registros_con_ajuste / stats.total_registros) * 100).toFixed(1)}%`
                : '0%'
              }
            </p>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Fecha Desde</label>
            <input
              type="date"
              value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700">Fecha Hasta</label>
            <input
              type="date"
              value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          
          <div className="flex items-end">
            <button
              onClick={() => {
                setFechaDesde('')
                setFechaHasta('')
              }}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Limpiar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <div className="text-center">
              <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
              <p className="mt-4 text-sm text-slate-500">Cargando inventario...</p>
            </div>
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <div className="mx-auto h-12 w-12 rounded-full bg-red-100 p-3">
              <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="mt-4 text-sm font-medium text-slate-900">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 text-sm font-medium text-blue-600 hover:text-blue-500"
            >
              Reintentar
            </button>
          </div>
        ) : inventory.length === 0 ? (
          <div className="p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-4 text-sm font-medium text-slate-900">No hay registros</p>
            <p className="mt-1 text-sm text-slate-500">
              Comienza importando un Excel o creando un registro manual
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Fecha
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Producto
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Stock Inicial
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Venta
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Stock Final
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Ajuste
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Precio Unit.
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Total
                  </th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {inventory.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm text-slate-900">
                      {new Date(item.fecha).toLocaleDateString('es-ES')}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">
                      {item.product_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-slate-900">
                      {formatNumber(item.stock_inicial)}
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium text-blue-600">
                      {formatNumber(item.venta_unidades)}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-slate-900">
                      {formatNumber(item.stock_final)}
                    </td>
                    <td className={`px-6 py-4 text-right text-sm font-medium ${item.ajuste !== 0 ? 'text-amber-600' : 'text-slate-400'}`}>
                      {item.ajuste !== 0 ? formatNumber(item.ajuste) : '-'}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-slate-600">
                      {formatCurrency(item.precio_unitario_venta)}
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium text-green-600">
                      {formatCurrency(item.importe_total)}
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      <Link
                        to={`${item.id}`}
                        className="text-blue-600 hover:text-blue-500"
                      >
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
