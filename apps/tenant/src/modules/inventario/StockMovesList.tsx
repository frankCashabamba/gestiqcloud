/**
 * Stock Moves List - Historial de movimientos
 */
import React, { useState, useEffect } from 'react'
import { listStockMoves, type StockMove } from './services'

export default function StockMovesList() {
  const [moves, setMoves] = useState<StockMove[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMoves()
  }, [])

  const loadMoves = async () => {
    try {
      const data = await listStockMoves({ limit: 100 })
      setMoves(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getKindLabel = (kind: string) => {
    const labels: Record<string, string> = {
      sale: 'Venta',
      purchase: 'Compra',
      adjustment: 'Ajuste',
      transfer: 'Transferencia',
      consume: 'Consumo',
    }
    return labels[kind] || kind
  }

  const getKindColor = (kind: string) => {
    const colors: Record<string, string> = {
      sale: 'bg-blue-100 text-blue-700',
      purchase: 'bg-green-100 text-green-700',
      adjustment: 'bg-amber-100 text-amber-700',
      consume: 'bg-purple-100 text-purple-700',
    }
    return colors[kind] || 'bg-slate-100 text-slate-700'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Movimientos de Stock</h1>
        <p className="mt-1 text-sm text-slate-500">Historial de entradas y salidas</p>
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
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Tipo</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Producto</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Cantidad</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {moves.map((move) => (
                <tr key={move.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm">
                    {new Date(move.created_at).toLocaleString('es-ES')}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getKindColor(move.kind)}`}>
                      {getKindLabel(move.kind)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-medium">
                    {move.product_id.substring(0, 8)}...
                  </td>
                  <td className="px-6 py-4 text-right text-sm font-bold">
                    {move.qty >= 0 ? '+' : ''}{move.qty.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {move.posted_at ? (
                      <span className="text-green-600">Contabilizado</span>
                    ) : (
                      <span className="text-slate-400">Borrador</span>
                    )}
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
