import React, { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const LeadsList = lazy(() => import('./pages/Leads/List'))
const LeadForm = lazy(() => import('./pages/Leads/Form'))
const OpportunitiesList = lazy(() => import('./pages/Opportunities/List'))
const OpportunityForm = lazy(() => import('./pages/Opportunities/Form'))

export default function CRMRoutes() {
  return (
    <ProtectedRoute
      permission="crm:read"
      fallback={<PermissionDenied permission="crm:read" />}
    >
      <Suspense fallback={<div>Cargando...</div>}>
        <Routes>
          <Route index element={<Dashboard />} />
          <Route path="leads" element={<LeadsList />} />
          <Route
            path="leads/new"
            element={
              <ProtectedRoute permission="crm:create">
                <LeadForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="leads/:id/edit"
            element={
              <ProtectedRoute permission="crm:update">
                <LeadForm />
              </ProtectedRoute>
            }
          />
          <Route path="opportunities" element={<OpportunitiesList />} />
          <Route
            path="opportunities/new"
            element={
              <ProtectedRoute permission="crm:create">
                <OpportunityForm />
              </ProtectedRoute>
            }
          />
          <Route
            path="opportunities/:id/edit"
            element={
              <ProtectedRoute permission="crm:update">
                <OpportunityForm />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="." replace />} />
        </Routes>
      </Suspense>
    </ProtectedRoute>
  )
}
