import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import EInvoicingDashboard from './EInvoicingDashboard'

export default function EinvoicingRoutes() {
  return (
    <ProtectedRoute
      permission="einvoicing:read"
      fallback={<PermissionDenied permission="einvoicing:read" />}
    >
      <Routes>
        <Route index element={<EInvoicingDashboard />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
