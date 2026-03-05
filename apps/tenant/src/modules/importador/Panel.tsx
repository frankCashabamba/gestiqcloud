import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import DocumentDetail from './pages/DocumentDetail'
import DocumentList from './pages/DocumentList'
import RecipeManager from './pages/RecipeManager'

export default function ImportadorPanel() {
  return (
    <Routes>
      <Route index element={<Dashboard />} />
      <Route path="upload" element={<UploadPage />} />
      <Route path="documents" element={<DocumentList />} />
      <Route path="documents/:id" element={<DocumentDetail />} />
      <Route path="recipes" element={<RecipeManager />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
