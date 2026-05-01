import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const TablesView = React.lazy(() => import('./TablesView'))
const OrderView = React.lazy(() => import('./OrderView'))
const KDSView = React.lazy(() => import('./KDSView'))

export default function RestaurantRoutes() {
  return (
    <ProtectedRoute
      permission="restaurant:read"
      fallback={<PermissionDenied permission="restaurant:read" />}
    >
      <RouterRoutes>
        <Route index element={<TablesView />} />
        <Route path="orders/:orderId" element={<OrderView />} />
        <Route
          path="kds"
          element={
            <ProtectedRoute
              permission="restaurant.kds.view"
              fallback={<PermissionDenied permission="restaurant.kds.view" />}
            >
              <KDSView />
            </ProtectedRoute>
          }
        />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
