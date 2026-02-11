import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ComprasList from './List'
import CompraForm from './Form'
import CompraDetail from './Detail'

export default function ComprasRoutes() {
  return (
    <ProtectedRoute
      permission="purchases:read"
      fallback={<PermissionDenied permission="purchases:read" />}
    >
      <Routes>
        <Route index element={<ComprasList />} />
        <Route
          path="new"
          element={
            <ProtectedRoute permission="purchases:create">
              <CompraForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="nueva"
          element={
            <ProtectedRoute permission="purchases:create">
              <CompraForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id" element={<CompraDetail />} />
        <Route
          path=":id/edit"
          element={
            <ProtectedRoute permission="purchases:update">
              <CompraForm />
            </ProtectedRoute>
          }
        />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="purchases:update">
              <CompraForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
