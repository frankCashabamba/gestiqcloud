import React, { useState, useEffect } from 'react'
import { useToast } from '../../shared/toast'
import {
  querySalesByMonth,
  queryTopProducts,
  queryLowStock,
  queryPaymentMovements,
  QueryResult,
} from './services'

export default function CopilotDashboard() {
  const { error: showError } = useToast()
  const [loading, setLoading] = useState(false)
  const [salesMonth, setSalesMonth] = useState<QueryResult | null>(null)
  const [topProducts, setTopProducts] = useState<QueryResult | null>(null)
  const [lowStock, setLowStock] = useState<QueryResult | null>(null)
  const [payments, setPayments] = useState<QueryResult | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [sales, top, stock, pay] = await Promise.all([
        querySalesByMonth().catch(() => null),
        queryTopProducts().catch(() => null),
        queryLowStock(5).catch(() => null),
        queryPaymentMovements().catch(() => null),
      ])
      setSalesMonth(sales)
      setTopProducts(top)
      setLowStock(stock)
      setPayments(pay)
    } catch {
      showError('Error cargando datos de Copilot')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">AI Copilot</h1>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Actualizar
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {salesMonth && (
          <Card title={salesMonth.cards[0]?.title || 'Ventas por Mes'}>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-64">
              {JSON.stringify(salesMonth.cards[0]?.series, null, 2)}
            </pre>
          </Card>
        )}

        {topProducts && (
          <Card title={topProducts.cards[0]?.title || 'Productos Top'}>
            <div className="space-y-2">
              {topProducts.cards[0]?.data?.slice(0, 5).map((item: any, idx: number) => (
                <div key={idx} className="flex justify-between text-sm">
                  <span>{item.name}</span>
                  <span className="font-bold">${item.importe?.toFixed(2) || 0}</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {lowStock && (
          <Card title={lowStock.cards[0]?.title || 'Stock Bajo'}>
            <div className="space-y-2">
              {lowStock.cards[0]?.data?.slice(0, 5).map((item: any, idx: number) => (
                <div key={idx} className="text-sm text-red-600">
                  {item.almacen}: {item.qty} unidades
                </div>
              ))}
            </div>
          </Card>
        )}

        {payments && (
          <Card title={payments.cards[0]?.title || 'Cobros/Pagos'}>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-64">
              {JSON.stringify(payments.cards[0]?.data, null, 2)}
            </pre>
          </Card>
        )}
      </div>

      <div className="text-xs text-gray-500 space-y-1">
        {salesMonth?.sql && <p>SQL: {salesMonth.sql}</p>}
      </div>
    </div>
  )
}

function Card({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      {children}
    </div>
  )
}
