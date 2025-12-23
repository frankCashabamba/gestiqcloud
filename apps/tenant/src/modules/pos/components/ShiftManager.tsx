/**
 * ShiftManager - Gestión de turnos de caja
 */
import React, { useState, useEffect } from 'react'
import { openShift, closeShift, getCurrentShift, getShiftSummary, getLastDailyCount } from '../services'
import type { POSShift, POSRegister, ShiftSummary } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'

interface ShiftManagerProps {
  register: POSRegister
  onShiftChange: (shift: POSShift | null) => void
}

export default function ShiftManager({ register, onShiftChange }: ShiftManagerProps) {
  const { symbol: currencySymbol, formatCurrency } = useCurrency()
  const [currentShift, setCurrentShift] = useState<POSShift | null>(null)
  const [loading, setLoading] = useState(false)
  const [openingFloat, setOpeningFloat] = useState('100.00')
  const [closingCash, setClosingCash] = useState('')
  const [lossAmount, setLossAmount] = useState('')
  const [lossNote, setLossNote] = useState('')
  const [showCloseModal, setShowCloseModal] = useState(false)
  const [summary, setSummary] = useState<ShiftSummary | null>(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [canEditClose, setCanEditClose] = useState(false)

  useEffect(() => {
    loadCurrentShift()
    loadSuggestedOpeningFloat()

    try {
      const rawProfile = JSON.parse(localStorage.getItem('userProfile') || 'null')
      const isAdmin = rawProfile?.es_admin_empresa || rawProfile?.is_company_admin
      setCanEditClose(!!isAdmin)
    } catch {
      setCanEditClose(false)
    }
  }, [register.id])

  const loadCurrentShift = async () => {
    try {
      const shift = await getCurrentShift(register.id)
      setCurrentShift(shift)
      onShiftChange(shift)
    } catch (error) {
      console.error('Error loading shift:', error)
    }
  }

  const loadSuggestedOpeningFloat = async () => {
    try {
      const lastCount = await getLastDailyCount(register.id)
      if (lastCount && lastCount.counted_cash > 0) {
        setOpeningFloat(lastCount.counted_cash.toFixed(2))
      }
    } catch (error) {
      console.error('Error loading suggested opening float:', error)
    }
  }

  const handleOpenShift = async () => {
    if (!openingFloat || parseFloat(openingFloat) < 0) {
      alert('Ingrese un monto de apertura válido')
      return
    }

    setLoading(true)
    try {
      const shift = await openShift({
        register_id: register.id,
        opening_float: parseFloat(openingFloat)
      })
      setCurrentShift(shift)
      onShiftChange(shift)
      alert('Turno abierto exitosamente')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al abrir turno')
    } finally {
      setLoading(false)
    }
  }

  const handleShowCloseModal = async () => {
    setShowCloseModal(true)
    if (currentShift) {
      setLoadingSummary(true)
      try {
        const shiftSummary = await getShiftSummary(currentShift.id)
        setSummary(shiftSummary)
        const cashTotal = shiftSummary.payments?.cash || shiftSummary.payments?.efectivo || 0
        if (cashTotal > 0) {
          setClosingCash(cashTotal.toFixed(2))
        }
      } catch (error: any) {
        console.error('Error loading summary:', error)
        alert('Error al cargar el resumen del turno')
      } finally {
        setLoadingSummary(false)
      }
    }
  }

  const handleCloseShift = async () => {
    if (!currentShift) return

    if (summary && summary.pending_receipts > 0) {
      alert(`No se puede cerrar el turno. Hay ${summary.pending_receipts} recibo(s) sin cobrar/terminar.`)
      return
    }

    if (!closingCash || parseFloat(closingCash) < 0) {
      alert('Ingrese el total de efectivo en caja')
      return
    }

    setLoading(true)
    try {
      const payload: any = {
        shift_id: currentShift.id,
        closing_cash: parseFloat(closingCash),
      }

      if (lossAmount && parseFloat(lossAmount) > 0) {
        payload.loss_amount = parseFloat(lossAmount)
      }
      if (lossNote) {
        payload.loss_note = lossNote
      }

      const result = await closeShift(payload)

      // Mostrar resumen del cierre
      const discrepancy = result.difference
      const msg = `Turno cerrado exitosamente!\n\n` +
        `Ventas Totales: ${formatCurrency(result.total_sales || 0)}\n` +
        `Ventas en Efectivo: ${formatCurrency(result.cash_sales || 0)}\n` +
        `Efectivo Esperado: ${formatCurrency(result.expected_cash || 0)}\n` +
        `Efectivo Contado: ${formatCurrency(result.counted_cash || 0)}\n` +
        `Diferencia: ${formatCurrency(discrepancy || 0)}` +
        (result.loss_amount > 0 ? `\nPérdidas: ${formatCurrency(result.loss_amount || 0)}` : '') +
        (result.loss_note ? `\nNota: ${result.loss_note}` : '')

      alert(msg)

      setCurrentShift(null)
      onShiftChange(null)
      setShowCloseModal(false)
      setClosingCash('')
      setLossAmount('')
      setLossNote('')
      setSummary(null)
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al cerrar turno')
    } finally {
      setLoading(false)
    }
  }

  if (!currentShift) {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-4">
        <h2 className="text-xl font-bold mb-4">Abrir Turno - {register.name}</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Monto de Apertura ({currencySymbol})
          <span className="text-xs text-gray-500 ml-2">(sugerido del cierre anterior)</span>
          </label>
          <input
            type="number"
            step="0.01"
            value={openingFloat}
          onChange={(e) => setOpeningFloat(e.target.value)}
          className="w-full px-3 py-2 border rounded"
          disabled={loading}
          />
        </div>
        <button
          onClick={handleOpenShift}
          disabled={loading}
          className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? 'Abriendo...' : 'Abrir Turno'}
        </button>
      </div>
    )
  }

  return (
    <>
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4 flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-green-800">Turno Abierto</h3>
          <p className="text-sm text-green-700">
            Apertura: {new Date(currentShift.opened_at).toLocaleString()} |
            Fondo: {currencySymbol}{(Number(currentShift.opening_float) || 0).toFixed(2)}
          </p>
        </div>
        <button
          onClick={handleShowCloseModal}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Cerrar Turno
        </button>
      </div>

      {showCloseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full m-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500 font-semibold">Cerrar Turno</p>
                <h3 className="text-2xl font-bold text-gray-900">Resumen y cierre de caja</h3>
                <p className="text-sm text-gray-600">Revisa ventas, stock restante y registra el efectivo contado.</p>
              </div>
              <button
                onClick={() => setShowCloseModal(false)}
                className="text-gray-400 hover:text-gray-600 text-lg font-bold px-2"
                aria-label="Cerrar modal"
              >
                ×
              </button>
            </div>

            {loadingSummary ? (
              <div className="py-8 text-center text-gray-500">Cargando resumen...</div>
            ) : summary ? (
              <>
                {/* Alertas */}
                {summary.pending_receipts > 0 && (
                  <div className="bg-red-50 border border-red-300 text-red-800 p-3 rounded mb-4">
                    ⚠️ Hay {summary.pending_receipts} recibo(s) sin cobrar/terminar. No se puede cerrar el turno.
                  </div>
                )}

                {/* Resumen de ventas */}
                <div className="mb-4 p-4 bg-blue-50 rounded border border-blue-100">
                  <h4 className="font-semibold mb-1 text-blue-900">Resumen de ventas</h4>
                  <p className="text-sm text-blue-900">Total de ventas: {formatCurrency(summary.sales_total)}</p>
                  <p className="text-sm text-blue-900">Productos vendidos: {summary.receipts_count}</p>
                </div>

                {/* Productos vendidos */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-900">Productos vendidos</h4>
                    <span className="text-xs text-gray-500">Stock restante por almacén</span>
                  </div>
                  <div className="max-h-60 overflow-y-auto border rounded shadow-sm">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-100 sticky top-0 text-gray-700">
                        <tr>
                          <th className="p-2 text-left">Código</th>
                          <th className="p-2 text-left">Producto</th>
                          <th className="p-2 text-right">Vendido</th>
                          <th className="p-2 text-right">Subtotal</th>
                          <th className="p-2 text-right">Stock Restante</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary.items_sold
                          .filter(item => item.qty_sold > 0)
                          .map((item, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="p-2">{item.code || '-'}</td>
                              <td className="p-2">{item.name}</td>
                              <td className="p-2 text-right">{item.qty_sold.toFixed(2)}</td>
                              <td className="p-2 text-right">{formatCurrency(item.subtotal)}</td>
                              <td className="p-2 text-right">
                                {item.stock.length > 0 ? (
                                  <div className="space-y-1">
                                    {item.stock.map((s, i) => (
                                      <div key={i} className={s.qty < 0 ? 'text-red-600 font-semibold' : s.qty === 0 ? 'text-gray-400' : ''}>
                                        {s.warehouse_name}: {s.qty.toFixed(2)}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : null}

            {/* Formulario de cierre */}
            <div className="space-y-4 border-t pt-4 mt-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium">Total en efectivo ({currencySymbol})</label>
                  {summary?.payments && (
                    <div className="text-xs text-gray-500 space-x-2 text-right">
                      <span>Efectivo registrado: {formatCurrency(summary.payments?.cash || summary.payments?.efectivo || 0)}</span>
                      {summary.payments?.card ? <span>Tarjeta: {formatCurrency(summary.payments.card)}</span> : null}
                      {summary.payments?.link ? <span>Link: {formatCurrency(summary.payments.link)}</span> : null}
                      {summary.payments?.store_credit ? <span>Vale: {formatCurrency(summary.payments.store_credit)}</span> : null}
                    </div>
                  )}
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={closingCash}
                  onChange={(e) => setClosingCash(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                  placeholder="0.00"
                  autoFocus
                  disabled={!canEditClose}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Pérdidas/Mermas ({currencySymbol})</label>
                <input
                  type="number"
                  step="0.01"
                  value={lossAmount}
                  onChange={(e) => setLossAmount(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                  placeholder="0.00"
                  disabled={!canEditClose}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Nota de Pérdidas</label>
                <textarea
                  value={lossNote}
                  onChange={(e) => setLossNote(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                  placeholder="Descripción de pérdidas o productos deteriorados..."
                  rows={3}
                  disabled={!canEditClose}
                />
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleCloseShift}
                disabled={loading || (summary?.pending_receipts ?? 0) > 0}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Cerrando...' : 'Cerrar Turno'}
              </button>
              <button
                onClick={() => {
                  setShowCloseModal(false)
                  setSummary(null)
                }}
                disabled={loading}
                className="flex-1 bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
