// apps/tenant/src/modules/inventario/Routes.tsx
import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import StockList from './StockListFixed'
import MovimientoForm from './MovementFormBulk'
import AlertConfigManager from './components/AlertConfigManager'

export default function InventarioRoutes() {
return (
<ProtectedRoute
  permission="inventory:read"
  fallback={<PermissionDenied permission="inventory:read" />}
>
<RouterRoutes>
<Route index element={<StockList />} />
  <Route
    path="movimientos/nuevo"
    element={
      <ProtectedRoute permission="inventory:create">
        <MovimientoForm />
      </ProtectedRoute>
    }
  />
    <Route path="alerts" element={<AlertConfigManager />} />
    </RouterRoutes>
</ProtectedRoute>
  )
}
