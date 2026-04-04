import React, { Suspense, lazy, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

const UploadPage = lazy(() => import('./pages/UploadPage'))
const DocumentDetail = lazy(() => import('./pages/DocumentDetail'))
const DocumentList = lazy(() => import('./pages/DocumentList'))

const RouteLoader = () => <div className="p-4">Loading...</div>

function LazyElement({ children }: { children: React.ReactElement }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function ImportadorRoutes() {
  useEffect(() => {
    void import('./services').then(({ loadDocCategoryKeywords, loadProductSheetDetectionConfig }) => {
      void loadDocCategoryKeywords()
      void loadProductSheetDetectionConfig()
    })
  }, [])

  return (
    <Routes>
      <Route index element={<Navigate to="documents" replace />} />
      <Route path="upload" element={<LazyElement><UploadPage /></LazyElement>} />
      <Route path="documents" element={<LazyElement><DocumentList /></LazyElement>} />
      <Route path="documents/:id" element={<LazyElement><DocumentDetail /></LazyElement>} />
      <Route path="*" element={<Navigate to="documents" replace />} />
    </Routes>
  )
}
