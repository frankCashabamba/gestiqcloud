import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import { useAuth } from '../../auth/AuthContext'
import PermissionDenied from '../../components/PermissionDenied'
import ImportadorExcelWithQueue from './ImportadorExcelWithQueue'
import BatchesList from './imports/BatchesList'
import BatchDetail from './imports/BatchDetail'
import ProductosImportados from './ImportedProducts'
import PreviewPage from './PreviewPage'
import ImportadorSettings from './pages/ImportadorSettings'
import TemplatesPage from './pages/TemplatesPage'
import { ImportQueueProvider } from './context/ImportQueueContext'
import { isCompanyAdmin } from './utils/companyAdmin'

export default function ImportadorRoutes() {
  const { profile, token } = useAuth()
  const canManageImporterSettings = isCompanyAdmin(profile, token)

  return (
    <ProtectedRoute
      permission="importer:read"
      fallback={<PermissionDenied permission="importer:read" />}
    >
      <ImportQueueProvider>
        <Routes>
          <Route index element={<ImportadorExcelWithQueue />} />
          {/* Wizard eliminado */}
          <Route path="preview" element={<PreviewPage />} />
          <Route path="products" element={<ProductosImportados />} />
          <Route path="templates" element={<TemplatesPage />} />
          <Route
            path="settings"
            element={
              canManageImporterSettings
                ? <ImportadorSettings />
                : <PermissionDenied permission="is_admin_company" />
            }
          />
          <Route path="batches" element={<BatchesList />} />
          <Route path="batches/:id" element={<BatchDetail />} />
          <Route path="pendientes" element={<Navigate to="../batches" replace />} />
          <Route path="*" element={<Navigate to="." replace />} />
        </Routes>
      </ImportQueueProvider>
    </ProtectedRoute>
  )
}
