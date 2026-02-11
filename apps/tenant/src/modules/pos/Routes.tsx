/**
 * POS Routes
 */
import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import POSView from './POSView'
import DailyCountsView from './components/DailyCountsView'

export default function POSRoutes() {
  return (
    <ProtectedRoute
      permission="pos:read"
      fallback={<PermissionDenied permission="pos:read" />}
    >
      <Routes>
        <Route path="/" element={<POSView />} />
        <Route path="daily-counts" element={<DailyCountsView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
