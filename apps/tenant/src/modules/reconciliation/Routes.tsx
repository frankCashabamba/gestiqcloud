import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ReconciliationDashboard from './ReconciliationDashboard'
import StatementDetail from './StatementDetail'

export default function ReconciliationRoutes() {
  return (
    <ProtectedRoute
      permission="reconciliation:read"
      fallback={<PermissionDenied permission="reconciliation:read" />}
    >
      <RouterRoutes>
        <Route index element={<ReconciliationDashboard />} />
        <Route path=":statementId" element={<StatementDetail />} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
