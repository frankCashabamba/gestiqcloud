/** DailyCountsView - Vista simple de cierres de caja */
import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listDailyCounts, listRegisters, getCurrentShift, getShiftSummary } from '../services'
import { useCurrency } from '../../../hooks/useCurrency'
import { useAuth } from '../../../auth/AuthContext'
import { listUsuarios } from '../../usuarios/services'
import type { Usuario } from '../../usuarios/types'
import type { ShiftSummary, POSShift } from '../../../types/pos'

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
  const cashierId = searchParams.get('cashier_id') || undefined
  const [counts, setCounts] = useState<DailyCount[]>([])
  const [registers, setRegisters] = useState<Register[]>([])
  const [openShift, setOpenShift] = useState<POSShift | null>(null)
  const [openSummary, setOpenSummary] = useState<ShiftSummary | null>(null)
  const [cashiers, setCashiers] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { symbol: currencySymbol } = useCurrency()
  const { profile } = useAuth()
  const esAdminEmpresa = !!(profile?.es_admin_empresa || (profile as any)?.is_company_admin)

  useEffect(() => {
    loadData()
  }, [registerId, cashierId])

  useEffect(() => {
    if (!esAdminEmpresa) return
    ;(async () => {
      try {
        const users = await listUsuarios()
        const actives = users.filter((u) => u.active)
        setCashiers(actives)
      } catch {
        // silencioso
      }
    })()
  }, [esAdminEmpresa])

  const loadData = async () => {
    try {
      setLoading(true)
      const regs = await listRegisters()
      setRegisters(regs.filter((r: any) => r.active))
      const params: any = { limit: 50 }
      if (registerId) params.register_id = registerId
      const data = await listDailyCounts(params)
      setCounts(data)
      const targetRegisterId = registerId || regs.find((r: any) => r.active)?.id
      if (targetRegisterId) {
        const current = await getCurrentShift(targetRegisterId)
        setOpenShift(current)
        if (current) {
          const summary = await getShiftSummary(current.id, cashierId ? { cashier_id: cashierId } : undefined)
          setOpenSummary(summary)
        } else {
          setOpenSummary(null)
        }
      } else {
        setOpenShift(null)
        setOpenSummary(null)
      }
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

  const handleCashierChange = (newCashierId: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (newCashierId) {
      newParams.set('cashier_id', newCashierId)
    } else {
      newParams.delete('cashier_id')
    }
    setSearchParams(newParams)
  }

  const formatCashierLabel = (u: Usuario) => {
    const name = `${u.first_name || ''} ${u.last_name || ''}`.trim()
    return name || u.username || u.email || (u.id ? `#${String(u.id).slice(0, 8)}` : '')
  }

  if (loading) {
    return <div className="p-4 text-center">Cargando resumen...</div>
  }

  if (error) {
    return <div className="p-4 text-center text-red-600">Error: {error}</div>
  }

  const latest = counts.length > 0 ? counts[0] : null
  const liveSalesTotal = openSummary?.sales_total ?? null
  const liveTickets = openSummary?.receipts_count ?? null
  const liveAvgTicket =
    liveSalesTotal !== null && liveTickets && liveTickets > 0 ? liveSalesTotal / liveTickets : null
  const cashTotal = openSummary?.payments?.cash ?? openSummary?.payments?.efectivo ?? 0
  const cardTotal = openSummary?.payments?.card ?? 0
  const linkTotal = openSummary?.payments?.link ?? 0
  const storeCreditTotal = openSummary?.payments?.store_credit ?? 0
  const otherTotal = openSummary
    ? Math.max(0, (liveSalesTotal || 0) - cashTotal - cardTotal - linkTotal - storeCreditTotal)
    : 0
  const registerName = openShift
    ? registers.find((r) => r.id === openShift.register_id)?.name
    : null
  const formatMoney = (value: number) => `${currencySymbol}${value.toFixed(2)}`

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold">Ventas del dia</h2>
          <p className="text-sm text-gray-500">Resumen simple para caja</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium">Caja:</label>
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
          {esAdminEmpresa && cashiers.length > 0 && (
            <>
              <label className="text-sm font-medium">Cajero:</label>
              <select
                value={cashierId || ''}
                onChange={(e) => handleCashierChange(e.target.value)}
                className="border rounded px-3 py-2"
              >
                <option value="">Todos</option>
                {cashiers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {formatCashierLabel(u)}
                  </option>
                ))}
              </select>
            </>
          )}
        </div>
      </div>

      {!latest && !openSummary ? (
        <div className="bg-white border rounded-lg p-6 text-gray-600">
          No hay cierres de caja aun. Cierra un turno para ver el resumen del dia.
        </div>
      ) : (
        <>
          <div className="bg-white border rounded-lg p-6 mb-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
              <div className="text-lg font-semibold">
                {openShift ? 'Turno abierto' : 'Hoy'}
              </div>
              <div className="text-sm text-gray-500">
                {openShift
                  ? `Caja ${registerName || openShift.register_id.slice(0, 6)}`
                  : latest
                  ? new Date(latest.count_date).toLocaleDateString()
                  : ''}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 mt-4">
              <div className="border rounded-lg p-4">
                <div className="text-xs text-gray-500">Total vendido</div>
                <div className="text-2xl font-semibold">
                  {formatMoney(liveSalesTotal ?? latest?.total_sales ?? 0)}
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-gray-500">Efectivo</div>
                <div className="text-xl font-semibold">
                  {formatMoney(openSummary ? cashTotal : latest?.cash_sales ?? 0)}
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-gray-500">Tarjeta</div>
                <div className="text-xl font-semibold">
                  {formatMoney(openSummary ? cardTotal : latest?.card_sales ?? 0)}
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-gray-500">Otros</div>
                <div className="text-xl font-semibold">
                  {formatMoney(openSummary ? otherTotal : latest?.other_sales ?? 0)}
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-gray-500">Tickets</div>
                <div className="text-xl font-semibold">
                  {liveTickets ?? 0}
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-gray-500">Ticket promedio</div>
                <div className="text-xl font-semibold">
                  {formatMoney(liveAvgTicket ?? 0)}
                </div>
              </div>
            </div>
            {!openSummary && latest ? (
              <div className="mt-4 text-sm text-gray-500">
                Datos basados en el ultimo cierre de caja.
              </div>
            ) : null}
          </div>

          <div className="bg-white border rounded-lg">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">Ultimos cierres</h3>
              <p className="text-sm text-gray-500">Ultimos 10 dias</p>
            </div>
            <div className="divide-y">
              {counts.slice(0, 10).map((count) => (
                <div key={count.id} className="px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                  <div>
                    <div className="font-medium">{new Date(count.count_date).toLocaleDateString()}</div>
                    <div className="text-xs text-gray-500">Fondo inicial: {formatMoney(count.opening_float)}</div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div>
                      <div className="text-gray-500">Total</div>
                      <div className="font-semibold">{formatMoney(count.total_sales)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Contado</div>
                      <div className="font-semibold">{formatMoney(count.counted_cash)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Diferencia</div>
                      <div className={`font-semibold ${count.discrepancy !== 0 ? 'text-red-600' : ''}`}>
                        {formatMoney(count.discrepancy)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
