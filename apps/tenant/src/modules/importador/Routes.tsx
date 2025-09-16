import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ImportadorExcel from './ImportadorExcel'
import ImportadorWizard from './Wizard'
import ImportadosList from './ImportadosList'

export default function ImportadorRoutes() {
  return (
    <Routes>
      <Route index element={<ImportadorExcel />} />
      <Route path="wizard" element={<ImportadorWizard />} />
      <Route path="pendientes" element={<ImportadosList />} />
    </Routes>
  )
}
