import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const TablesView = React.lazy(() => import('./TablesView'))
const OrderView = React.lazy(() => import('./OrderView'))

export default function RestaurantRoutes() {
  return (
    <ProtectedRoute
      permission="restaurant:read"
      fallback={<PermissionDenied permission="restaurant:read" />}
    >
      <RouterRoutes>
        <Route index element={<TablesView />} />
        <Route path="orders/:orderId" element={<OrderView />} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
