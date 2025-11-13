import React from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { useImportQueue } from '../context/ImportQueueContext'

export default function ProcessingIndicator() {
  const { queue, processingCount, isProcessing } = useImportQueue()
  const { empresa } = useParams()
  const location = useLocation()

  // Extraer empresa de la URL si useParams no funciona (por estar fuera del contexto de rutas)
  const empresaFromUrl = React.useMemo(() => {
    if (empresa) return empresa
    const match = location.pathname.match(/^\/([^/]+)\//)
    return match ? match[1] : 'kusi-panaderia'
  }, [empresa, location.pathname])

  if (!isProcessing && processingCount === 0) return null

  const pendingCount = queue.filter((item) => item.status === 'pending').length
  const readyCount = queue.filter((item) => item.status === 'ready').length
  const errorCount = queue.filter((item) => item.status === 'error').length

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <div className="rounded-lg border border-blue-200 bg-white shadow-lg">
        <div className="flex items-center gap-3 border-b border-neutral-100 px-4 py-3">
          <div className="flex h-8 w-8 items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
          </div>
          <div className="flex-1">
            <div className="text-sm font-medium text-neutral-900">
              Procesando archivos en segundo plano
            </div>
            <div className="text-xs text-neutral-500">
              {processingCount} procesando
              {pendingCount > 0 && `, ${pendingCount} pendiente${pendingCount > 1 ? 's' : ''}`}
              {readyCount > 0 && `, ${readyCount} listo${readyCount > 1 ? 's' : ''}`}
              {errorCount > 0 && `, ${errorCount} con error${errorCount > 1 ? 'es' : ''}`}
            </div>
          </div>
        </div>

        <div className="space-y-1 p-2">
          {queue
            .filter((item) => item.status === 'processing' || item.status === 'pending')
            .slice(0, 3)
            .map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-2 rounded px-2 py-1.5 text-xs"
              >
                <div className="flex h-4 w-4 shrink-0 items-center justify-center">
                  {item.status === 'processing' ? (
                    <div className="h-3 w-3 animate-spin rounded-full border border-blue-500 border-t-transparent"></div>
                  ) : (
                    <div className="h-2 w-2 rounded-full bg-neutral-300"></div>
                  )}
                </div>
                <div className="flex-1 truncate text-neutral-700">{item.name}</div>
              </div>
            ))}

          {queue.filter((item) => item.status === 'processing' || item.status === 'pending')
            .length > 3 && (
            <div className="px-2 py-1 text-center text-xs text-neutral-500">
              +{queue.filter((item) => item.status === 'processing' || item.status === 'pending')
                .length - 3}{' '}
              más...
            </div>
          )}
        </div>

        <div className="border-t border-neutral-100 px-4 py-2 text-center">
          <Link
            to={`/${empresaFromUrl}/mod/imports`}
            className="text-xs font-medium text-blue-600 hover:text-blue-700"
          >
            Ver detalles →
          </Link>
        </div>
      </div>
    </div>
  )
}
