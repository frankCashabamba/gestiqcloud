import React from 'react'
import { Link } from 'react-router-dom'

export default function SectoresPanel() {
  return (
    <div style={{ padding: 16 }}>
      <h2 className="text-xl font-semibold mb-3">Facturación por sectores</h2>
      <p className="text-sm text-gray-600 mb-4">Elige un sector para crear facturas con campos específicos.</p>
      <ul className="list-disc list-inside">
        <li><Link to="taller" className="text-blue-700">Taller</Link></li>
        <li><Link to="panaderia" className="text-blue-700">Panadería</Link></li>
      </ul>
    </div>
  )
}
