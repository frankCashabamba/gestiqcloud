import React from 'react'

export type EstadoFactura = 'borrador' | 'emitida' | 'anulada' | string | undefined

export default function FacturaStatusBadge({ estado }: { estado: EstadoFactura }) {
  const e = (estado || '').toLowerCase()
  const style =
    e === 'emitida'
      ? { background: '#dcfce7', color: '#166534' }
      : e === 'anulada'
      ? { background: '#fee2e2', color: '#991b1b' }
      : { background: '#f3f4f6', color: '#111827' }

  const label = e ? e.charAt(0).toUpperCase() + e.slice(1) : '-'

  return (
    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600, ...style }}>{label}</span>
  )
}
