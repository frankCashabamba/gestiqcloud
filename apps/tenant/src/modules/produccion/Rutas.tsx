import React from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * Rutas de horneado/producción
 * Vista ligera para lanzar una nueva ruta (orden) de horneado.
 * Por ahora redirige al formulario existente de orden de producción.
 */
export default function Rutas() {
  const nav = useNavigate()
  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Rutas de Horneado</h2>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded"
          onClick={() => nav('../ordenes/nuevo')}
        >
          Nueva ruta
        </button>
      </div>
      <p className="text-sm text-gray-600 mb-2">
        Esta vista agrupa las órdenes de producción programadas para horneado.
      </p>
      <div className="border rounded p-4 bg-white">
        <p className="text-gray-700 text-sm">
          Próximamente: tablero de rutas en horno, estados en tiempo real y asignación por tanda.
        </p>
      </div>
    </div>
  )
}

