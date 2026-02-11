// apps/tenant/src/modules/products/Routes.tsx
import React from 'react'
import { Route, Routes as RouterRoutes, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ProductosList from './List'
import ProductoForm from './Form'
import ProductosPurge from './actions/PurgeAll'

export default function ProductosRoutes() {
  return (
    <ProtectedRoute
      permission="products:read"
      fallback={<PermissionDenied permission="products:read" />}
    >
      <RouterRoutes>
        <Route index element={<ProductosList />} />
        <Route
          path="purge"
          element={
            <ProtectedRoute permission="products:delete">
              <ProductosPurge />
            </ProtectedRoute>
          }
        />
        <Route
          path="nuevo"
          element={
            <ProtectedRoute permission="products:create">
              <ProductoForm />
            </ProtectedRoute>
          }
        />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="products:update">
              <ProductoForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
