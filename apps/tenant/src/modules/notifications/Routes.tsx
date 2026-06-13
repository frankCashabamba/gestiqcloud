import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import NotificationCenter from './NotificationCenter'

export default function NotificationsRoutes() {
  return (
    <ProtectedRoute
      permission="notifications:read"
      fallback={<PermissionDenied permission="notifications:read" />}
    >
      <Routes>
        <Route path="/" element={<NotificationCenter />} />
      </Routes>
    </ProtectedRoute>
  )
}
