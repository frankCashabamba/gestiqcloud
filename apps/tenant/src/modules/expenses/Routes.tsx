import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import GastosList from './List'
import GastoForm from './Form'
import GastoDetail from './Detail'

export default function GastosRoutes() {
  return (
    <ProtectedRoute
      permission="expenses:read"
      fallback={<PermissionDenied permission="expenses:read" />}
    >
      <Routes>
        <Route index element={<GastosList />} />
        <Route
          path="nuevo"
          element={
            <ProtectedRoute permission="expenses:create">
              <GastoForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id" element={<GastoDetail />} />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="expenses:update">
              <GastoForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
