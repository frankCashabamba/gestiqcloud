import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ConfigViewer from './ConfigViewer'

export default function TemplatesRoutes() {
  return (
    <ProtectedRoute
      permission="templates:manage"
      fallback={<PermissionDenied permission="templates:manage" />}
    >
      <Routes>
        <Route path="/" element={<ConfigViewer />} />
      </Routes>
    </ProtectedRoute>
  )
}
