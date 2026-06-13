import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ClientesList from './List'
import ClienteForm from './Form'

export default function ClientesRoutes() {
  return (
    <ProtectedRoute
      permission="customers:read"
      fallback={<PermissionDenied permission="customers:read" />}
    >
      <Routes>
        <Route index element={<ClientesList />} />
        <Route
          path="new"
          element={
            <ProtectedRoute permission="customers:create">
              <ClienteForm />
            </ProtectedRoute>
          }
        />
        <Route path="nuevo" element={<Navigate to="../new" replace />} />
        <Route
          path=":id/edit"
          element={
            <ProtectedRoute permission="customers:update">
              <ClienteForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id/editar" element={<Navigate to="../edit" replace />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
