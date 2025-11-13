import React from 'react'

export type EstadoVenta = 'borrador' | 'emitida' | 'anulada' | 'facturada' | string | undefined

export default function StatusBadge({ estado }: { estado: EstadoVenta }) {
  const e = (estado || '').toLowerCase()
  const style =
    e === 'emitida'
      ? { background: '#dcfce7', color: '#166534', border: '1px solid #86efac' }
      : e === 'facturada'
      ? { background: '#dbeafe', color: '#1e40af', border: '1px solid #93c5fd' }
      : e === 'anulada'
      ? { background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5' }
      : { background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db' }

  const label = e ? e.charAt(0).toUpperCase() + e.slice(1) : '-'

  return (
    <span style={{ 
      padding: '3px 10px', 
      borderRadius: 999, 
      fontSize: 11, 
      fontWeight: 600, 
      textTransform: 'uppercase',
      letterSpacing: '0.02em',
      display: 'inline-block',
      ...style 
    }}>
      {label}
    </span>
  )
}

