/**
 * EinvoiceStatus - Componente para mostrar estado de e-factura
 */

import React, { useState, useEffect } from 'react'
import { sendEinvoice, getEinvoiceStatus, getEinvoiceStatusColor } from '../services'
import type { EinvoiceStatus } from '../services'

interface EinvoiceStatusProps {
  invoiceId: string
  country: 'ES' | 'EC'
  canSend?: boolean
}

export default function EinvoiceStatus({ invoiceId, country, canSend = true }: EinvoiceStatusProps) {
  const [status, setStatus] = useState<EinvoiceStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStatus()
  }, [invoiceId])

  const loadStatus = async () => {
    try {
      setLoading(true)
      const statusData = await getEinvoiceStatus(invoiceId)
      setStatus(statusData)
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError('Error al cargar estado')
      }
      // 404 significa que no se ha enviado aún, es normal
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    try {
      setSending(true)
      setError(null)
      await sendEinvoice({ invoice_id: invoiceId, country })
      // Recargar estado después de un delay
      setTimeout(loadStatus, 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al enviar e-factura')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return <span className="text-gray-500">Cargando...</span>
  }

  if (!status) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-gray-500">No enviada</span>
        {canSend && (
          <button
            onClick={handleSend}
            disabled={sending}
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {sending ? 'Enviando...' : `Enviar ${country === 'ES' ? 'Facturae' : 'SRI'}`}
          </button>
        )}
      </div>
    )
  }

  const statusColor = getEinvoiceStatusColor(status.status)

  return (
    <div className="flex items-center gap-2">
      <span
        className={`px-2 py-1 text-xs rounded-full text-white ${
          statusColor === 'green' ? 'bg-green-500' :
          statusColor === 'yellow' ? 'bg-yellow-500' :
          statusColor === 'blue' ? 'bg-blue-500' :
          'bg-red-500'
        }`}
      >
        {status.status}
      </span>

      {status.clave_acceso && (
        <span className="text-xs text-gray-500">
          {country === 'EC' ? 'Recibo' : 'Ref'}: {status.clave_acceso}
        </span>
      )}

      {status.error_message && (
        <span className="text-xs text-red-600" title={status.error_message}>
          ⚠️ Error
        </span>
      )}

      {status.submitted_at && (
        <span className="text-xs text-gray-500">
          {new Date(status.submitted_at).toLocaleDateString()}
        </span>
      )}

      <button
        onClick={loadStatus}
        className="text-xs text-blue-600 hover:text-blue-800"
        title="Actualizar estado"
      >
        ↻
      </button>

      {error && (
        <span className="text-xs text-red-600">{error}</span>
      )}
    </div>
  )
}
