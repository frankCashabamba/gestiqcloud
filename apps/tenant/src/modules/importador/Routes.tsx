import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ImportadorExcel from './ImportadorExcel'
import ImportadorExcelWithQueue from './ImportadorExcelWithQueue'
import ImportadorWizard from './Wizard'
import ImportadosList from './ImportadosList'
import BatchesList from './imports/BatchesList'
import BatchDetail from './imports/BatchDetail'
import ProductosImportados from './ProductosImportados'
import PreviewPage from './PreviewPage'
import { ImportQueueProvider } from './context/ImportQueueContext'

export default function ImportadorRoutes() {
  return (
    <ImportQueueProvider>
      <Routes>
        <Route index element={<ImportadorExcelWithQueue />} />
        <Route path="legacy" element={<ImportadorExcel />} />
        <Route path="wizard" element={<ImportadorWizard />} />
        <Route path="pendientes" element={<ImportadosList />} />
        <Route path="preview" element={<PreviewPage />} />
        <Route path="products" element={<ProductosImportados />} />
        <Route path="batches" element={<BatchesList />} />
        <Route path="batches/:id" element={<BatchDetail />} />
      </Routes>
    </ImportQueueProvider>
  )
}
