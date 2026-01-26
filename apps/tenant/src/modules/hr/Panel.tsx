import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import VacationsList from './VacationsList'
import FichajesView from './FichajesView'
import NominaView from './NominaView'

function Index() {
  return (
    <div style={{ padding: 16 }}>
      <h2>HR</h2>
      <ul>
        <li><Link to="vacaciones">Vacations</Link></li>
        <li><Link to="fichajes">Timekeeping</Link></li>
        <li><Link to="nomina">Payroll</Link></li>
      </ul>
    </div>
  )
}

export default function RRHHRoutes() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="vacaciones" element={<VacacionesList />} />
      <Route path="fichajes" element={<FichajesView />} />
      <Route path="nomina" element={<NominaView />} />
      <Route path="*" element={<Navigate to="vacaciones" replace />} />
    </Routes>
  )
}
