/**
 * POS Dashboard - Vista principal de caja
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getCurrentShift, listRegisters, type POSShift, type POSRegister } from './services'
import ShiftManager from './ShiftManager'

export default function Dashboard() {
  const [registers, setRegisters] = useState<POSRegister[]>([])
  const [selectedRegister, setSelectedRegister] = useState<number | null>(null)
  const [currentShift, setCurrentShift] = useState<POSShift | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRegisters()
  }, [])

  useEffect(() => {
    if (selectedRegister) {
      loadCurrentShift()
    }
  }, [selectedRegister])

  const loadRegisters = async () => {
    try {
      const data = await listRegisters()
      setRegisters(data)
      if (data.length > 0 && !selectedRegister) {
        setSelectedRegister(data[0].id)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadCurrentShift = async () => {
    if (!selectedRegister) return
    
    try {
      const shift = await getCurrentShift(selectedRegister)
      setCurrentShift(shift)
    } catch (err) {
      setCurrentShift(null)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(value)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Punto de Venta</h1>
          <p className="mt-1 text-sm text-slate-500">Gestión de caja y ventas</p>
        </div>
        
        {/* Selector de Caja */}
        {registers.length > 1 && (
          <select
            value={selectedRegister || ''}
            onChange={(e) => setSelectedRegister(Number(e.target.value))}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium"
          >
            {registers.map((reg) => (
              <option key={reg.id} value={reg.id}>
                {reg.name || `Caja ${reg.code}`}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Estado del Turno */}
      {currentShift ? (
        <div className="rounded-xl border-2 border-green-200 bg-green-50 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="rounded-full bg-green-600 p-3">
                <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold text-green-900">Turno Abierto</h2>
                <p className="text-sm text-green-700">
                  Desde {new Date(currentShift.opened_at).toLocaleTimeString('es-ES')}
                </p>
              </div>
            </div>
            
            <div className="text-right">
              <p className="text-sm text-green-700">Fondo Inicial</p>
              <p className="text-2xl font-bold text-green-900">
                {formatCurrency(currentShift.opening_float)}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border-2 border-slate-200 bg-slate-50 p-6">
          <div className="text-center">
            <div className="mx-auto rounded-full bg-slate-200 p-3 w-fit">
              <svg className="h-6 w-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 className="mt-4 text-xl font-bold text-slate-900">Turno Cerrado</h2>
            <p className="mt-1 text-sm text-slate-600">Abre un turno para comenzar a vender</p>
          </div>
        </div>
      )}

      {/* Shift Manager */}
      {selectedRegister && (
        <ShiftManager
          registerId={selectedRegister}
          currentShift={currentShift}
          onShiftChange={loadCurrentShift}
        />
      )}

      {/* Acciones Principales */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link
          to="nuevo-ticket"
          className={`flex items-center gap-4 rounded-xl border-2 p-6 transition ${
            currentShift
              ? 'border-blue-200 bg-blue-50 hover:border-blue-300 hover:bg-blue-100'
              : 'border-slate-200 bg-slate-50 cursor-not-allowed opacity-60'
          }`}
          onClick={(e) => !currentShift && e.preventDefault()}
        >
          <div className="rounded-lg bg-blue-600 p-3">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Nuevo Ticket</h3>
            <p className="text-sm text-slate-600">Crear venta</p>
          </div>
        </Link>

        <Link
          to="historial"
          className="flex items-center gap-4 rounded-xl border-2 border-slate-200 bg-white p-6 hover:border-slate-300 hover:bg-slate-50"
        >
          <div className="rounded-lg bg-slate-600 p-3">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Historial</h3>
            <p className="text-sm text-slate-600">Ver tickets</p>
          </div>
        </Link>

        <Link
          to="turnos"
          className="flex items-center gap-4 rounded-xl border-2 border-slate-200 bg-white p-6 hover:border-slate-300 hover:bg-slate-50"
        >
          <div className="rounded-lg bg-purple-600 p-3">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Turnos</h3>
            <p className="text-sm text-slate-600">Gestión turnos</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
