import React from 'react'
import { Routes, Route, Navigate, useParams } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import VentasList from './List'
import VentaForm from './Form'
import VentaDetail from './Detail'

function CrmOpportunitiesRedirect() {
  const { empresa } = useParams<{ empresa: string }>()
  return <Navigate to={`/${empresa}/crm/opportunities?pending=1`} replace />
}

export default function VentasRoutes() {
  return (
    <ProtectedRoute
      permission="sales:read"
      fallback={<PermissionDenied permission="sales:read" />}
    >
      <Routes>
        <Route index element={<VentasList />} />
        <Route
          path="new"
          element={
            <ProtectedRoute permission="sales:create">
              <VentaForm />
            </ProtectedRoute>
          }
        />
        <Route path="opportunities" element={<CrmOpportunitiesRedirect />} />
        <Route path="orders" element={<Navigate to="." replace />} />
        <Route path=":id" element={<VentaDetail />} />
        <Route
          path=":id/edit"
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
