import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import CajaList from './CajaList'
import BancoList from './BancoList'

function Index() {
  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-2">Finanzas</h2>
      <ul className="list-disc pl-6">
        <li><Link to="caja">Caja</Link></li>
        <li><Link to="bancos">Bancos</Link></li>
      </ul>
    </div>
  )
}

export default function FinanzasRoutes() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="caja" element={<CajaList />} />
      <Route path="bancos" element={<BancoList />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

