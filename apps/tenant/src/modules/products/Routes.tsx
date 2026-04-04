// apps/tenant/src/modules/products/Routes.tsx
import React, { Suspense, lazy } from 'react'
import { Route, Routes as RouterRoutes, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const ProductosList = lazy(() => import('./List'))
const ProductoForm = lazy(() => import('./Form'))
const ProductosPurge = lazy(() => import('./actions/PurgeAll'))
const RawMaterialsList = lazy(() => import('./RawMaterialsList'))

const RouteLoader = () => <div className="p-4">Loading...</div>

function LazyElement({ children }: { children: React.ReactElement }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function ProductosRoutes() {
  return (
    <ProtectedRoute
      permission="products:read"
      fallback={<PermissionDenied permission="products:read" />}
    >
      <RouterRoutes>
        <Route index element={<LazyElement><ProductosList /></LazyElement>} />
        <Route
          path="purge"
          element={
            <ProtectedRoute permission="products:delete">
              <LazyElement><ProductosPurge /></LazyElement>
            </ProtectedRoute>
          }
        />
        <Route
          path="nuevo"
          element={
            <ProtectedRoute permission="products:create">
              <LazyElement><ProductoForm /></LazyElement>
            </ProtectedRoute>
          }
        />
        <Route path="materias-primas" element={<LazyElement><RawMaterialsList /></LazyElement>} />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="products:update">
              <LazyElement><ProductoForm /></LazyElement>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </RouterRoutes>
    </ProtectedRoute>
  )
}
