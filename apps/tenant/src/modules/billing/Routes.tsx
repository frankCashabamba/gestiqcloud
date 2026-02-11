import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import FacturasList from './List'
import FacturaForm from './Form'
import FacturaePage from './InvoiceE'
import SectoresRoutes from './sectores/Routes'

export default function FacturacionRoutes() {
  return (
    <ProtectedRoute
      permission="billing:read"
      fallback={<PermissionDenied permission="billing:read" />}
    >
      <Routes>
        <Route index element={<FacturasList />} />
        <Route
          path="nueva"
          element={
            <ProtectedRoute permission="billing:create">
              <FacturaForm />
            </ProtectedRoute>
          }
        />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="billing:update">
              <FacturaForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id/facturae" element={<FacturaePage />} />
        <Route path="sectores/*" element={<SectoresRoutes />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
