import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import DocumentDetail from './pages/DocumentDetail'
import DocumentList from './pages/DocumentList'
import { loadDocCategoryKeywords, loadProductSheetDetectionConfig } from './services'

export default function ImportadorRoutes() {
  useEffect(() => {
    void loadDocCategoryKeywords()
    void loadProductSheetDetectionConfig()
  }, [])

  return (
    <Routes>
      <Route index element={<Navigate to="documents" replace />} />
      <Route path="upload" element={<UploadPage />} />
      <Route path="documents" element={<DocumentList />} />
      <Route path="documents/:id" element={<DocumentDetail />} />
      <Route path="recipes" element={<Navigate to="../upload" replace />} />
      <Route path="*" element={<Navigate to="documents" replace />} />
    </Routes>
  )
}
