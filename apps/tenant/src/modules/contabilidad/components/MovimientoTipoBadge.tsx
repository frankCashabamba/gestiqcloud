import React from 'react'

export type TipoMovimiento = 'ingreso' | 'gasto'

export const MovimientoTipoBadge: React.FC<{ tipo: TipoMovimiento }> = ({ tipo }) => {
  const style = tipo === 'ingreso' ? { background: '#dcfce7', color: '#166534' } : { background: '#fee2e2', color: '#991b1b' }
  return (
    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600, ...style }}>
      {tipo.toUpperCase()}
    </span>
  )
}

