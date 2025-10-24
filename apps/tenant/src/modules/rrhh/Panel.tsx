import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import VacacionesList from './VacacionesList'
import FichajesView from './FichajesView'
import NominaView from './NominaView'

function Index() {
  return (
    <div style={{ padding: 16 }}>
      <h2>RRHH</h2>
      <ul>
        <li><Link to="vacaciones">Vacaciones</Link></li>
        <li><Link to="fichajes">Fichajes</Link></li>
        <li><Link to="nomina">Nómina</Link></li>
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
