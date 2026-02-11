import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ImportadorExcelWithQueue from './ImportadorExcelWithQueue'
import ImportadorWizard from './Wizard'
import BatchesList from './imports/BatchesList'
import BatchDetail from './imports/BatchDetail'
import ProductosImportados from './ImportedProducts'
import PreviewPage from './PreviewPage'
import { ImportQueueProvider } from './context/ImportQueueContext'

export default function ImportadorRoutes() {
  return (
    <ProtectedRoute
      permission="importer:read"
      fallback={<PermissionDenied permission="importer:read" />}
    >
      <ImportQueueProvider>
        <Routes>
          <Route index element={<ImportadorExcelWithQueue />} />
          <Route
            path="wizard"
            element={
              <ProtectedRoute permission="importer:create">
                <ImportadorWizard />
              </ProtectedRoute>
            }
          />
          <Route path="preview" element={<PreviewPage />} />
          <Route path="products" element={<ProductosImportados />} />
          <Route path="batches" element={<BatchesList />} />
          <Route path="batches/:id" element={<BatchDetail />} />
          <Route path="*" element={<Navigate to="." replace />} />
        </Routes>
      </ImportQueueProvider>
    </ProtectedRoute>
  )
}
