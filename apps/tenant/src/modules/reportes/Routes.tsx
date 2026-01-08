import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import MarginsDashboard from './MarginsDashboard'

export default function ReportesRoutes() {
  return (
    <RouterRoutes>
      <Route index element={<MarginsDashboard />} />
    </RouterRoutes>
  )
}
