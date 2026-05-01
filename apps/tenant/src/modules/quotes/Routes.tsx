import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import QuotesList from './QuotesList'
import QuoteForm from './QuoteForm'
import QuoteDetail from './QuoteDetail'

export default function QuotesRoutes() {
  return (
    <ProtectedRoute
      permission="quotes:manage"
      fallback={<PermissionDenied permission="quotes:manage" />}
    >
      <Routes>
        <Route index element={<QuotesList />} />
        <Route path="new" element={<QuoteForm />} />
        <Route path=":id" element={<QuoteDetail />} />
        <Route path=":id/edit" element={<QuoteForm />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
