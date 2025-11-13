import React, { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const LeadsList = lazy(() => import('./pages/Leads/List'))
const LeadForm = lazy(() => import('./pages/Leads/Form'))
const OpportunitiesList = lazy(() => import('./pages/Opportunities/List'))
const OpportunityForm = lazy(() => import('./pages/Opportunities/Form'))

export default function CRMRoutes() {
  return (
    <Suspense fallback={<div>Cargando...</div>}>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<LeadsList />} />
        <Route path="leads/new" element={<LeadForm />} />
        <Route path="leads/:id/edit" element={<LeadForm />} />
        <Route path="opportunities" element={<OpportunitiesList />} />
        <Route path="opportunities/new" element={<OpportunityForm />} />
        <Route path="opportunities/:id/edit" element={<OpportunityForm />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </Suspense>
  )
}
