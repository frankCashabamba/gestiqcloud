import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ReportsDashboard from './ReportsDashboard'
import SalesReport from './SalesReport'
import InventoryReport from './InventoryReport'
import FinancialReport from './FinancialReport'
import MarginsDashboard from './MarginsDashboard'

export default function ReportesRoutes() {
  return (
    <ProtectedRoute
      permission="reportes:read"
      fallback={<PermissionDenied permission="reportes:read" />}
    >
      <RouterRoutes>
        <Route index element={<ReportsDashboard />} />
        <Route path="ventas" element={<SalesReport />} />
        <Route path="inventario" element={<InventoryReport />} />
        <Route path="financiero" element={<FinancialReport />} />
        <Route path="margenes" element={<MarginsDashboard />} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
