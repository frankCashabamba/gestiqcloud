/**
 * IncidentDetailModal.tsx
 * Modal de detalle de incidencia con análisis IA
 */

import React from 'react'
import type { Incident } from '../types/incidents'

interface Props {
  incident: Incident
  onClose: () => void
  onAnalyze: (id: string) => void
  onAutoResolve: (id: string) => void
  onAssign: (id: string) => void
  onCloseIncident: (id: string) => void
}

export default function IncidentDetailModal({
  incident,
  onClose,
  onAnalyze,
  onAutoResolve,
  onAssign,
  onCloseIncident
}: Props) {
  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-300'
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-300'
      default: return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-gray-900">🔍 Detalle de Incidencia</h3>
            <span className={`px-3 py-1 text-sm font-bold rounded border ${getSeverityColor(incident.severidad)}`}>
              {incident.severidad.toUpperCase()}
            </span>
            {incident.auto_detected && (
              <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded font-medium">
                🤖 Auto-detectada
              </span>
            )}
            {incident.auto_resolved && (
              <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded font-medium">
                ✨ Auto-resuelta
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Información General */}
          <section className="mb-6">
            <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Información General</h4>
            <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-gray-500 mb-1">ID</div>
                <div className="text-sm font-mono text-gray-900">{incident.id}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Tipo</div>
                <div className="text-sm font-medium text-gray-900">{incident.tipo}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Tenant</div>
                <div className="text-sm font-mono text-gray-900">
                  {incident.tenant_id || 'Sistema'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Usuario</div>
                <div className="text-sm font-mono text-gray-900">
                  {incident.user_id || '-'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Estado</div>
                <div className="text-sm font-medium text-gray-900">{incident.estado}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Asignado a</div>
                <div className="text-sm font-mono text-gray-900">
                  {incident.assigned_to || 'Sin asignar'}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Creada</div>
                <div className="text-sm text-gray-900">{formatDate(incident.created_at)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Actualizada</div>
                <div className="text-sm text-gray-900">{formatDate(incident.updated_at)}</div>
              </div>
              {incident.resolved_at && (
                <div className="col-span-2">
                  <div className="text-xs text-gray-500 mb-1">Resuelta</div>
                  <div className="text-sm text-green-700 font-medium">
                    {formatDate(incident.resolved_at)}
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Título y Descripción */}
          <section className="mb-6">
            <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Descripción</h4>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h5 className="font-bold text-gray-900 text-lg mb-2">{incident.titulo}</h5>
              <p className="text-gray-700 whitespace-pre-wrap">{incident.description}</p>
            </div>
          </section>

          {/* Stack Trace */}
          {incident.stack_trace && (
            <section className="mb-6">
              <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Stack Trace</h4>
              <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-xs font-mono leading-relaxed">
                {incident.stack_trace}
              </pre>
            </section>
          )}

          {/* Metadata */}
          {incident.metadata && Object.keys(incident.metadata).length > 0 && (
            <section className="mb-6">
              <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Metadata</h4>
              <pre className="bg-gray-50 border border-gray-200 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                {JSON.stringify(incident.metadata, null, 2)}
              </pre>
            </section>
          )}

          {/* Análisis IA */}
          {incident.ia_analysis && (
            <section className="mb-6">
              <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3 flex items-center gap-2">
                <span>🤖 Análisis IA</span>
                <span className="text-xs font-normal text-gray-400">
                  Generado automáticamente
                </span>
              </h4>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                  {typeof incident.ia_analysis === 'string'
                    ? incident.ia_analysis
                    : JSON.stringify(incident.ia_analysis, null, 2)
                  }
                </pre>
              </div>

              {incident.ia_suggestion && (
                <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-2">
                    <span className="text-2xl">💡</span>
                    <div className="flex-1">
                      <h5 className="font-semibold text-blue-900 mb-2">Sugerencia de Resolución</h5>
                      <pre className="text-sm text-blue-800 whitespace-pre-wrap font-sans">
                        {incident.ia_suggestion}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Notas de Resolución */}
          {incident.resolution_notes && (
            <section className="mb-6">
              <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Notas de Resolución</h4>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm text-green-900 whitespace-pre-wrap">
                  {incident.resolution_notes}
                </p>
              </div>
            </section>
          )}
        </div>

        {/* Actions Footer */}
        {incident.estado !== 'resolved' && incident.estado !== 'closed' && (
          <div className="p-4 border-t border-gray-200 bg-gray-50 flex gap-3 justify-end">
            <button
              onClick={() => onAnalyze(incident.id)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium flex items-center gap-2"
            >
              🤖 Analizar con IA
            </button>
            <button
              onClick={() => onAutoResolve(incident.id)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium flex items-center gap-2"
            >
              ✨ Auto-Resolver
            </button>
            <button
              onClick={() => onAssign(incident.id)}
              className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium flex items-center gap-2"
            >
              👤 Asignarme
            </button>
            <button
              onClick={() => onCloseIncident(incident.id)}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium flex items-center gap-2"
            >
              ✅ Cerrar
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
