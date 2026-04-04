/**
 * POS Routes
 */
import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const POSView = lazy(() => import('./POSView'))
const DailyCountsView = lazy(() => import('./components/DailyCountsView'))

const RouteLoader = () => <div className="p-4">Loading...</div>

function LazyElement({ children }: { children: React.ReactElement }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function POSRoutes() {
  return (
    <ProtectedRoute
      permission="pos:read"
      fallback={<PermissionDenied permission="pos:read" />}
    >
      <Routes>
        <Route path="/" element={<LazyElement><POSView /></LazyElement>} />
        <Route path="daily-counts" element={<LazyElement><DailyCountsView /></LazyElement>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
