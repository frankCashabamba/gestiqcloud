import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import GeneralSettings from './General'
import BrandingSettings from './Branding'
import FiscalSettings from './Fiscal'
import HorariosSettings from './Horarios'
import LimitesSettings from './Limites'
import ModulosPanel from './ModulosPanel'

function Index() {
  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-2">Settings</h2>
      <ul className="list-disc pl-6">
        <li><Link to="general">General</Link></li>
        <li><Link to="modulos">Módulos</Link></li>
        <li><Link to="branding">Branding</Link></li>
        <li><Link to="fiscal">Fiscal</Link></li>
        <li><Link to="horarios">Horarios</Link></li>
        <li><Link to="limites">Límites</Link></li>
      </ul>
    </div>
  )
}

export default function SettingsRoutes() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="general" element={<GeneralSettings />} />
      <Route path="modulos" element={<ModulosPanel />} />
      <Route path="branding" element={<BrandingSettings />} />
      <Route path="fiscal" element={<FiscalSettings />} />
      <Route path="horarios" element={<HorariosSettings />} />
      <Route path="limites" element={<LimitesSettings />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
