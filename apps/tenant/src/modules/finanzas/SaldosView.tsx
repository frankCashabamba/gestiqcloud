import React, { useEffect, useState } from 'react'
import { getSaldos } from './services'
import type { SaldosResumen } from './types'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useNavigate } from 'react-router-dom'

export default function SaldosView() {
  const [saldos, setSaldos] = useState<SaldosResumen | null>(null)
  const [loading, setLoading] = useState(true)
  const { error } = useToast()
  const nav = useNavigate()

  useEffect(() => {
    loadSaldos()
  }, [])

  const loadSaldos = async () => {
    try {
      setLoading(true)
      const data = await getSaldos()
      setSaldos(data)
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="text-gray-500">Cargando saldos...</div>
      </div>
    )
  }

  if (!saldos) {
    return (
      <div className="p-4">
        <div className="text-red-600">Error al cargar saldos</div>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-2xl font-semibold">Resumen de Saldos</h2>
          <p className="text-sm text-gray-600 mt-1">
            Última actualización: {new Date(saldos.ultimo_update).toLocaleString()}
          </p>
        </div>
        <button
          onClick={loadSaldos}
          className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
        >
          Actualizar
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div
          className="bg-blue-50 border border-blue-200 rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => nav('/finanzas/caja')}
        >
          <div className="text-sm text-gray-600 mb-2">Caja</div>
          <div className="text-3xl font-bold text-blue-900">
            ${saldos.caja_total.toFixed(2)}
          </div>
          <div className="text-xs text-blue-600 mt-2">Ver movimientos →</div>
        </div>

        <div
          className="bg-green-50 border border-green-200 rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => nav('/finanzas/bancos')}
        >
          <div className="text-sm text-gray-600 mb-2">Bancos</div>
          <div className="text-3xl font-bold text-green-900">
            ${saldos.bancos_total.toFixed(2)}
          </div>
          <div className="text-xs text-green-600 mt-2">Ver movimientos →</div>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
          <div className="text-sm text-gray-600 mb-2">Total Disponible</div>
          <div className="text-3xl font-bold text-purple-900">
            ${saldos.total_disponible.toFixed(2)}
          </div>
          <div className="text-xs text-gray-500 mt-2">Caja + Bancos</div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="text-sm text-gray-600 mb-2">Pendiente Conciliar</div>
          <div className="text-3xl font-bold text-yellow-900">
            ${saldos.pendiente_conciliar.toFixed(2)}
          </div>
          <div className="text-xs text-yellow-600 mt-2">Requiere atención</div>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">Distribución de Saldos</h3>
        
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Caja</span>
              <span className="font-medium">
                {saldos.total_disponible > 0 
                  ? ((saldos.caja_total / saldos.total_disponible) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ 
                  width: saldos.total_disponible > 0
                    ? `${(saldos.caja_total / saldos.total_disponible) * 100}%`
                    : '0%'
                }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Bancos</span>
              <span className="font-medium">
                {saldos.total_disponible > 0 
                  ? ((saldos.bancos_total / saldos.total_disponible) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{ 
                  width: saldos.total_disponible > 0
                    ? `${(saldos.bancos_total / saldos.total_disponible) * 100}%`
                    : '0%'
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 border rounded-lg p-4">
          <h4 className="font-medium mb-3">Acciones Rápidas</h4>
          <div className="space-y-2">
            <button
              onClick={() => nav('/finanzas/caja')}
              className="w-full text-left px-3 py-2 bg-white border rounded hover:bg-gray-50"
            >
              📥 Registrar ingreso en caja
            </button>
            <button
              onClick={() => nav('/finanzas/caja')}
              className="w-full text-left px-3 py-2 bg-white border rounded hover:bg-gray-50"
            >
              📤 Registrar egreso en caja
            </button>
            <button
              onClick={() => nav('/finanzas/bancos')}
              className="w-full text-left px-3 py-2 bg-white border rounded hover:bg-gray-50"
            >
              🏦 Ver movimientos bancarios
            </button>
          </div>
        </div>

        <div className="bg-gray-50 border rounded-lg p-4">
          <h4 className="font-medium mb-3">Alertas</h4>
          {saldos.pendiente_conciliar > 0 ? (
            <div className="bg-yellow-100 border border-yellow-300 rounded px-3 py-2 text-sm">
              ⚠️ Tienes ${saldos.pendiente_conciliar.toFixed(2)} pendientes de conciliar
            </div>
          ) : (
            <div className="bg-green-100 border border-green-300 rounded px-3 py-2 text-sm">
              ✓ Todos los movimientos están conciliados
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
