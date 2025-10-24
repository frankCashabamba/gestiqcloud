import React, { useMemo } from 'react'
import { useMovimientos } from '../hooks/useMovimientos'

export const PerdidasGanancias: React.FC = () => {
  const { asientos, loading } = useMovimientos()

  const { ingresos, gastos, resultado } = useMemo(() => {
    let inc = 0
    let gas = 0
    for (const a of asientos) {
      for (const ap of a.apuntes) {
        if (ap.cuenta.startsWith('7')) inc += ap.haber ?? 0
        if (ap.cuenta.startsWith('6')) gas += ap.debe ?? 0
      }
    }
    return { ingresos: inc, gastos: gas, resultado: inc - gas }
  }, [asientos])

  if (loading) return <div style={{ padding: 16 }}>Calculando PyG…</div>

  return (
    <div style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff', margin: 16 }}>
      <h2 style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Cuenta de Pérdidas y Ganancias</h2>
      <div style={{ display: 'grid', gap: 6, color: '#111827' }}>
        <div>Ingresos: $ {ingresos.toFixed(2)}</div>
        <div>Gastos: $ {gastos.toFixed(2)}</div>
        <div style={{ fontWeight: 600 }}>Resultado del ejercicio: $ {resultado.toFixed(2)}</div>
      </div>
    </div>
  )
}

