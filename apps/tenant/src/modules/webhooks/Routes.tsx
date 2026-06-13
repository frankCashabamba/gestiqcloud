import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import SubscriptionsList from './SubscriptionsList'

export default function WebhooksRoutes() {
  return (
    <ProtectedRoute
      permission="webhooks:manage"
      fallback={<PermissionDenied permission="webhooks:manage" />}
    >
      <Routes>
        <Route path="/" element={<SubscriptionsList />} />
      </Routes>
    </ProtectedRoute>
  )
}
