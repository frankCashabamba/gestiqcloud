import React, { Suspense, lazy } from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const ReportsDashboard = lazy(() => import('./ReportsDashboard'))
const SalesReport = lazy(() => import('./SalesReport'))
const InventoryReport = lazy(() => import('./InventoryReport'))
const FinancialReport = lazy(() => import('./FinancialReport'))
const MarginsDashboard = lazy(() => import('./MarginsDashboard'))
const RealProfitReport = lazy(() => import('./RealProfitReport'))

const RouteLoader = () => <div className="p-4">Loading...</div>

function LazyElement({ children }: { children: React.ReactElement }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function ReportesRoutes() {
  return (
    <ProtectedRoute
      permission="reports:read"
      fallback={<PermissionDenied permission="reports:read" />}
    >
      <RouterRoutes>
        <Route index element={<LazyElement><ReportsDashboard /></LazyElement>} />
        <Route path="ventas" element={<LazyElement><SalesReport /></LazyElement>} />
        <Route path="inventario" element={<LazyElement><InventoryReport /></LazyElement>} />
        <Route path="financiero" element={<LazyElement><FinancialReport /></LazyElement>} />
        <Route path="resultado-real" element={<LazyElement><RealProfitReport /></LazyElement>} />
        <Route path="margenes" element={<LazyElement><MarginsDashboard /></LazyElement>} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
