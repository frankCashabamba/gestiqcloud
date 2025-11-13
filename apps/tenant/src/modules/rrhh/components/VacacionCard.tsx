import React from 'react'
import type { Vacacion } from '../../../types/rrhh'

interface Props {
  vacacion: Vacacion
  onAprobar?: (id: string) => void
  onRechazar?: (id: string) => void
}

export default function VacacionCard({ vacacion, onAprobar, onRechazar }: Props) {
  const estadoColor =
    vacacion.estado === 'aprobada'
      ? 'bg-green-100 border-green-300 text-green-800'
      : vacacion.estado === 'rechazada'
      ? 'bg-red-100 border-red-300 text-red-800'
      : vacacion.estado === 'cancelada'
      ? 'bg-gray-100 border-gray-300 text-gray-800'
      : 'bg-yellow-100 border-yellow-300 text-yellow-800'

  const tipoLabel = vacacion.tipo.replace('_', ' ')

  return (
    <div className={`border rounded-lg p-4 ${estadoColor}`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-semibold capitalize">{tipoLabel}</h4>
          <p className="text-xs mt-1">Empleado: {vacacion.empleado_id}</p>
        </div>
        <span className="text-xs font-medium uppercase px-2 py-1 rounded bg-white border">
          {vacacion.estado}
        </span>
      </div>

      <div className="text-sm space-y-1">
        <p>
          <strong>Desde:</strong> {vacacion.fecha_inicio}
        </p>
        <p>
          <strong>Hasta:</strong> {vacacion.fecha_fin}
        </p>
        <p>
          <strong>Días:</strong> {vacacion.dias}
        </p>
        {vacacion.motivo && (
          <p>
            <strong>Motivo:</strong> {vacacion.motivo}
          </p>
        )}
        {vacacion.notas && (
          <p className="text-xs text-gray-600 mt-2">
            <em>{vacacion.notas}</em>
          </p>
        )}
      </div>

      {vacacion.estado === 'pendiente' && (onAprobar || onRechazar) && (
        <div className="flex gap-2 mt-3">
          {onAprobar && (
            <button
              onClick={() => onAprobar(vacacion.id)}
              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
            >
              Aprobar
            </button>
          )}
          {onRechazar && (
            <button
              onClick={() => onRechazar(vacacion.id)}
              className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
            >
              Rechazar
            </button>
          )}
        </div>
      )}

      {vacacion.aprobado_por && (
        <p className="text-xs text-gray-600 mt-3">
          {vacacion.estado === 'aprobada' ? 'Aprobado' : 'Rechazado'} por: {vacacion.aprobado_por}
          {vacacion.fecha_aprobacion && ` el ${vacacion.fecha_aprobacion}`}
        </p>
      )}
    </div>
  )
}
