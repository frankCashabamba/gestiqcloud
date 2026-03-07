import React from 'react'

export type EstadoFactura = 'borrador' | 'emitida' | 'anulada' | string | undefined

export default function FacturaStatusBadge({ estado }: { estado: EstadoFactura }) {
  const e = (estado || '').toLowerCase()
  const style =
    e === 'emitida' || e === 'issued'
      ? { background: '#dcfce7', color: '#166534' }
      : e === 'anulada' || e === 'voided'
      ? { background: '#fee2e2', color: '#991b1b' }
      : e === 'pending_payment'
      ? { background: '#fef3c7', color: '#92400e' }
      : { background: '#f3f4f6', color: '#111827' }

  const label =
    e === 'pending_payment' ? 'Pdte. cobro'
    : e === 'issued' ? 'Emitida'
    : e === 'voided' ? 'Anulada'
    : e ? e.charAt(0).toUpperCase() + e.slice(1) : '-'

  return (
    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600, ...style }}>{label}</span>
  )
}
