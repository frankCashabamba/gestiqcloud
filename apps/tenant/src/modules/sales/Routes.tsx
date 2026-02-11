import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import VentasList from './List'
import VentaForm from './Form'
import VentaDetail from './Detail'

export default function VentasRoutes() {
  return (
    <ProtectedRoute
      permission="sales:read"
      fallback={<PermissionDenied permission="sales:read" />}
    >
      <Routes>
        <Route index element={<VentasList />} />
        <Route
          path="nueva"
          element={
            <ProtectedRoute permission="sales:create">
              <VentaForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id" element={<VentaDetail />} />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="sales:update">
              <VentaForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
