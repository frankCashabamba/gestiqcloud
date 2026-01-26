import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ImportadorExcelWithQueue from './ImportadorExcelWithQueue'
import ImportadorWizard from './Wizard'
import BatchesList from './imports/BatchesList'
import BatchDetail from './imports/BatchDetail'
import ProductosImportados from './ImportedProducts'
import PreviewPage from './PreviewPage'
import { ImportQueueProvider } from './context/ImportQueueContext'

export default function ImportadorRoutes() {
  return (
    <ImportQueueProvider>
      <Routes>
        <Route index element={<ImportadorExcelWithQueue />} />
        <Route path="wizard" element={<ImportadorWizard />} />
        <Route path="preview" element={<PreviewPage />} />
        <Route path="products" element={<ProductosImportados />} />
        <Route path="batches" element={<BatchesList />} />
        <Route path="batches/:id" element={<BatchDetail />} />
      </Routes>
    </ImportQueueProvider>
  )
}
