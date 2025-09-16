import React from 'react'
import { Routes, Route, Link, Navigate } from 'react-router-dom'
import { LibroDiario } from './components/LibroDiario'
import { LibroMayor } from './components/LibroMayor'
import { ConciliacionBancaria } from './components/ConciliacionBancaria'
import { PlanContable } from './components/PlanContable'
import { DashboardContable } from './components/DashboardContable'
import { MovimientoTable } from './components/MovimientoTable'
import { PerdidasGanancias } from './components/PerdidasGanancias'
import { useMovimientos } from './hooks/useMovimientos'

function Index() {
  return (
    <div style={{ padding: 16 }}>
      <h2>Contabilidad</h2>
      <ul>
        <li><Link to="dashboard">Dashboard</Link></li>
        <li><Link to="movimientos">Movimientos</Link></li>
        <li><Link to="libro-diario">Libro Diario</Link></li>
        <li><Link to="libro-mayor">Libro Mayor</Link></li>
        <li><Link to="pyl">Pérdidas y Ganancias</Link></li>
        <li><Link to="plan-contable">Plan contable</Link></li>
        <li><Link to="conciliacion">Conciliación bancaria</Link></li>
      </ul>
    </div>
  )
}

export default function ContabilidadPanel() {
  const { asientos, loading } = useMovimientos()
  return (
    <Routes>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<DashboardContable />} />
      <Route
        path="movimientos"
        element={loading ? <div style={{ padding: 16 }}>Cargando movimientos…</div> : <MovimientoTable asientos={asientos} />}
      />
      <Route path="libro-diario" element={<LibroDiario />} />
      <Route path="libro-mayor" element={<LibroMayor />} />
      <Route path="pyl" element={<PerdidasGanancias />} />
      <Route path="conciliacion" element={<ConciliacionBancaria />} />
      <Route path="plan-contable" element={<PlanContable />} />
      <Route path="*" element={<Navigate to="dashboard" replace />} />
    </Routes>
  )
}

