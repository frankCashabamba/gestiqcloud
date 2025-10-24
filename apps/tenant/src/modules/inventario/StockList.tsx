/**
 * Stock List - Listado de stock actual
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listStock, type StockItem } from './services'

export default function StockList() {
  const [stock, setStock] = useState<StockItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStock()
  }, [])

  const loadStock = async () => {
    try {
      const data = await listStock()
      setStock(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Stock Actual</h1>
          <p className="mt-1 text-sm text-slate-500">Inventario por almacén</p>
        </div>
        <Link
          to="ajustes"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          Nuevo Ajuste
        </Link>
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
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Producto</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Almacén</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Cantidad</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Lote</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Caduca</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {stock.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-medium">{item.product_id.substring(0, 8)}...</td>
                  <td className="px-6 py-4 text-sm">{item.warehouse_id.substring(0, 8)}...</td>
                  <td className={`px-6 py-4 text-right text-sm font-bold ${item.qty_on_hand < 10 ? 'text-red-600' : 'text-green-600'}`}>
                    {item.qty_on_hand.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">{item.lot || '-'}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {item.expires_at ? new Date(item.expires_at).toLocaleDateString('es-ES') : '-'}
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
