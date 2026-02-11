import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ReconciliationPlaceholder from './Placeholder'

export default function ReconciliationRoutes() {
  return (
    <ProtectedRoute
      permission="reconciliation:read"
      fallback={<PermissionDenied permission="reconciliation:read" />}
    >
      <Routes>
        <Route index element={<ReconciliationPlaceholder />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
