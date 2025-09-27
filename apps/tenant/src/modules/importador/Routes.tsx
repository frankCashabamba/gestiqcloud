import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ImportadorExcel from './ImportadorExcel'
import ImportadorWizard from './Wizard'
import ImportadosList from './ImportadosList'
import BatchesList from './imports/BatchesList'
import BatchDetail from './imports/BatchDetail'

export default function ImportadorRoutes() {
  return (
    <Routes>
      <Route index element={<ImportadorExcel />} />
      <Route path="wizard" element={<ImportadorWizard />} />
      <Route path="pendientes" element={<ImportadosList />} />
      <Route path="batches" element={<BatchesList />} />
      <Route path="batches/:id" element={<BatchDetail />} />
    </Routes>
  )
}
