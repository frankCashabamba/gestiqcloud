import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import MarginsDashboard from './MarginsDashboard'

export default function ReportesRoutes() {
  return (
    <ProtectedRoute
      permission="reportes:read"
      fallback={<PermissionDenied permission="reportes:read" />}
    >
      <RouterRoutes>
        <Route index element={<MarginsDashboard />} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
