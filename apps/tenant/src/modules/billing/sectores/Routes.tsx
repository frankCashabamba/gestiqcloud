import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import SectoresPanel from './SectoresPanel'
import TallerFacturaPage from './taller/TallerFacturaPage'
import PanaderiaFacturaPage from './panaderia/PanaderiaFacturaPage'

export default function SectoresRoutes() {
  return (
    <Routes>
      <Route index element={<SectoresPanel />} />
      <Route path="taller" element={<TallerFacturaPage />} />
      <Route path="panaderia" element={<PanaderiaFacturaPage />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
