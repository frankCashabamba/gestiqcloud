import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import Dashboard from './Dashboard'

export default function AnalyticsRoutes() {
  return (
    <ProtectedRoute
      permission="analytics:view"
      fallback={<PermissionDenied permission="analytics:view" />}
    >
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
