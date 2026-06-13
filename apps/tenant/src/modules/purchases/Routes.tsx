import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import PurchasesList from './List'
import PurchaseForm from './Form'
import PurchaseDetail from './Detail'

export default function PurchasesRoutes() {
  return (
    <ProtectedRoute
      permission="purchases:read"
      fallback={<PermissionDenied permission="purchases:read" />}
    >
      <Routes>
        <Route index element={<PurchasesList />} />
        <Route
          path="new"
          element={
            <ProtectedRoute permission="purchases:create">
              <PurchaseForm />
            </ProtectedRoute>
          }
        />
        <Route path="nuevo" element={<Navigate to="../new" replace />} />
        <Route path=":id" element={<PurchaseDetail />} />
        <Route
          path=":id/edit"
          element={
            <ProtectedRoute permission="purchases:update">
              <PurchaseForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id/editar" element={<Navigate to="../edit" replace />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
