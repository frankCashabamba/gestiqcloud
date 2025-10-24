/**
 * ShiftManager - Gestión de turnos de caja
 */
import React, { useState, useEffect } from 'react'
import { openShift, closeShift, getCurrentShift } from '../services'
import type { POSShift, POSRegister } from '../../../types/pos'

interface ShiftManagerProps {
  register: POSRegister
  onShiftChange: (shift: POSShift | null) => void
}

export default function ShiftManager({ register, onShiftChange }: ShiftManagerProps) {
  const [currentShift, setCurrentShift] = useState<POSShift | null>(null)
  const [loading, setLoading] = useState(false)
  const [openingFloat, setOpeningFloat] = useState('100.00')
  const [closingTotal, setClosingTotal] = useState('')
  const [showCloseModal, setShowCloseModal] = useState(false)

  useEffect(() => {
    loadCurrentShift()
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

  const handleCloseShift = async () => {
    if (!currentShift) return
    if (!closingTotal || parseFloat(closingTotal) < 0) {
      alert('Ingrese el total de cierre')
      return
    }

    setLoading(true)
    try {
      await closeShift({
        shift_id: currentShift.id,
        closing_total: parseFloat(closingTotal)
      })
      setCurrentShift(null)
      onShiftChange(null)
      setShowCloseModal(false)
      alert('Turno cerrado exitosamente')
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
          <label className="block text-sm font-medium mb-2">Monto de Apertura (€)</label>
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
            Fondo: €{currentShift.opening_float.toFixed(2)}
          </p>
        </div>
        <button
          onClick={() => setShowCloseModal(true)}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Cerrar Turno
        </button>
      </div>

      {showCloseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Cerrar Turno</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Total en Caja (€)</label>
              <input
                type="number"
                step="0.01"
                value={closingTotal}
                onChange={(e) => setClosingTotal(e.target.value)}
                className="w-full px-3 py-2 border rounded"
                placeholder="0.00"
                autoFocus
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCloseShift}
                disabled={loading}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
              >
                {loading ? 'Cerrando...' : 'Cerrar Turno'}
              </button>
              <button
                onClick={() => setShowCloseModal(false)}
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
