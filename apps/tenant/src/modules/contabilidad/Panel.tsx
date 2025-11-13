import React from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { MovimientoTable } from './components/MovimientoTable'
import { useMovimientos } from './hooks/useMovimientos'

const NAV_LINKS = [
  { to: 'dashboard', label: 'Dashboard' },
  { to: 'movimientos', label: 'Movimientos' },
  { to: 'libro-diario', label: 'Libro Diario' },
  { to: 'libro-mayor', label: 'Libro Mayor' },
  { to: 'pyl', label: 'Pérdidas y Ganancias' },
  { to: 'plan-contable', label: 'Plan Contable' },
  { to: 'conciliacion', label: 'Conciliación bancaria' },
]

export function MovimientosPage() {
  const { asientos, loading } = useMovimientos()
  if (loading) {
    return <div style={{ padding: 16 }}>Cargando movimientos…</div>
  }
  return <MovimientoTable asientos={asientos} />
}

export default function ContabilidadPanel() {
  return (
    <div className="contabilidad-panel md:flex gap-6 p-4">
      <nav className="md:w-64 mb-4 md:mb-0">
        <h2 className="text-lg font-semibold mb-3">Contabilidad</h2>
        <ul className="space-y-2">
          {NAV_LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded ${isActive ? 'bg-blue-100 text-blue-800 font-medium' : 'hover:bg-gray-100'}`
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex-1">
        <Outlet />
      </div>
    </div>
  )
}
