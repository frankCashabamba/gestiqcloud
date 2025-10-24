import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import FacturasList from './List'
import FacturaForm from './Form'
import FacturaePage from './Facturae'
import SectoresRoutes from './sectores/Routes'

export default function FacturacionRoutes() {
  return (
    <Routes>
      <Route index element={<FacturasList />} />
      <Route path="nueva" element={<FacturaForm />} />
      <Route path=":id/editar" element={<FacturaForm />} />
      <Route path=":id/facturae" element={<FacturaePage />} />
      <Route path="sectores/*" element={<SectoresRoutes />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
