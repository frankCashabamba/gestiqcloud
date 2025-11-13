import React, { useMemo } from 'react'
import { useMovimientos } from '../hooks/useMovimientos'

export const DashboardContable: React.FC = () => {
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

  if (loading) return <div style={{ padding: 16 }}>Cargando dashboard…</div>

  const Box = ({ label, value }: { label: string, value: string | number }) => (
    <div style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
      <div style={{ color: '#64748b', fontSize: 12 }}>{label}</div>
      <div style={{ fontWeight: 700, fontSize: 20 }}>{value}</div>
    </div>
  )

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        <Box label="Ingresos Totales" value={`$ ${ingresos.toFixed(2)}`} />
        <Box label="Gastos Totales" value={`$ ${gastos.toFixed(2)}`} />
        <Box label="Resultado" value={`$ ${resultado.toFixed(2)}`} />
      </div>
    </div>
  )
}
