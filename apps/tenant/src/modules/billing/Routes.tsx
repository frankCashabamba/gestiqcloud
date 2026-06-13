import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import InvoicesList from './List'
import InvoiceForm from './Form'
import InvoiceEPage from './InvoiceE'

export default function InvoiceRoutes() {
  return (
    <ProtectedRoute
      permission="billing:read"
      fallback={<PermissionDenied permission="billing:read" />}
    >
      <Routes>
        <Route index element={<InvoicesList />} />
        <Route
          path="new"
          element={
            <ProtectedRoute permission="billing:create">
              <InvoiceForm />
            </ProtectedRoute>
          }
        />
        <Route path="nueva" element={<Navigate to="../new" replace />} />
        <Route path="nuevo" element={<Navigate to="../new" replace />} />
        <Route
          path=":id/edit"
          element={
            <ProtectedRoute permission="billing:update">
              <InvoiceForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id/editar" element={<Navigate to="../edit" replace />} />
        <Route path=":id/facturae" element={<InvoiceEPage />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
