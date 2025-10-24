/**
 * Shift Manager - Gestión de turnos de caja
 */
import React, { useState } from 'react'
import { openShift, closeShift, type POSShift } from './services'

type ShiftManagerProps = {
  registerId: string
  currentShift: POSShift | null
  onShiftChange: () => void
}

export default function ShiftManager({ registerId, currentShift, onShiftChange }: ShiftManagerProps) {
  const [openingFloat, setOpeningFloat] = useState('0')
  const [closingTotal, setClosingTotal] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleOpenShift = async () => {
    try {
      setLoading(true)
      setError(null)
      
      await openShift({
        register_id: registerId,
        opening_float: parseFloat(openingFloat) || 0,
      })
      
      setOpeningFloat('0')
      onShiftChange()
    } catch (err: any) {
      setError(err.message || 'Error al abrir turno')
    } finally {
      setLoading(false)
    }
  }

  const handleCloseShift = async () => {
    if (!currentShift) return
    
    if (!closingTotal || parseFloat(closingTotal) < 0) {
      setError('Ingrese el total de cierre')
      return
    }
    
    try {
      setLoading(true)
      setError(null)
      
      await closeShift({
        shift_id: currentShift.id,
        closing_total: parseFloat(closingTotal),
      })
      
      setClosingTotal('')
      onShiftChange()
    } catch (err: any) {
      setError(err.message || 'Error al cerrar turno')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Gestión de Turno</h2>
      
      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!currentShift ? (
        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Fondo Inicial (€)
            </label>
            <input
              type="number"
              step="0.01"
              value={openingFloat}
              onChange={(e) => setOpeningFloat(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              placeholder="0.00"
            />
          </div>
          
          <button
            onClick={handleOpenShift}
            disabled={loading}
            className="w-full rounded-lg bg-green-600 px-6 py-3 font-medium text-white hover:bg-green-500 disabled:bg-slate-300"
          >
            {loading ? 'Abriendo...' : 'Abrir Turno'}
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="rounded-lg bg-slate-50 p-4">
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Turno ID:</span>
              <span className="font-mono text-slate-900">{currentShift.id}</span>
            </div>
            <div className="mt-2 flex justify-between text-sm">
              <span className="text-slate-600">Inicio:</span>
              <span className="font-medium text-slate-900">
                {new Date(currentShift.opened_at).toLocaleString('es-ES')}
              </span>
            </div>
            <div className="mt-2 flex justify-between">
              <span className="text-slate-600">Fondo Inicial:</span>
              <span className="text-xl font-bold text-green-600">
                {new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(currentShift.opening_float)}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Total de Cierre (€)
            </label>
            <input
              type="number"
              step="0.01"
              value={closingTotal}
              onChange={(e) => setClosingTotal(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              placeholder="0.00"
            />
            <p className="mt-1 text-xs text-slate-500">
              Cuenta el efectivo total en caja
            </p>
          </div>

          <button
            onClick={handleCloseShift}
            disabled={loading}
            className="w-full rounded-lg bg-red-600 px-6 py-3 font-medium text-white hover:bg-red-500 disabled:bg-slate-300"
          >
            {loading ? 'Cerrando...' : 'Cerrar Turno'}
          </button>
        </div>
      )}
    </div>
  )
}
