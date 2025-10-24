// src/pages/AdminPanel.tsx
import React from 'react'
import { LayoutAdmin } from '../style/LayoutAdmin'
import { useAuthGuard } from '../hooks/useAuthGuard'
import { AdminCard } from '../components/AdminCard'
//import { EmpresaModuloList } from '../modules/modulos/EmpresaModuloList'
import './admin-panel.css'

export default function AdminPanel() {
  useAuthGuard('superadmin')

  const modulos = [
    { nombre: 'Empresas', descripcion: 'Gestión de empresas registradas.', icono: '/icons/empresas.png', url_completa: 'empresas' },
    { nombre: 'Usuarios Principales', descripcion: 'Control de usuarios del sistema.', icono: '/icons/usuario.png', url_completa: 'usuarios' },
    { nombre: 'Configuración de sistemas', descripcion: 'Sólo las configuraciones del sistema.', icono: '/icons/configuracion.jpeg', url_completa: '/admin/configuracion' },
    { nombre: 'Migraciones', descripcion: 'Ejecutar migraciones (Render Job)', icono: '/icons/configuracion.jpeg', url_completa: 'ops/migraciones' },
  ]

  return (
      <div className="admin-container">
        <header><h1 className="admin-title">🛠️ Panel de Administración</h1></header>

        <section className="admin-section">
          <h2>⚙️ Administración del SaaS</h2>
          <div className="admin-grid">
            {modulos.map((m) => (
              <AdminCard
                key={m.url_completa}
                href={m.url_completa}
                iconSrc={m.icono}
                iconSize="sm"
                title={m.nombre}
                description={m.descripcion}
              />
            ))}
          </div>
        </section>

        <section className="admin-section">
          <h2>📦 Módulos del sistema activos</h2>
          <div className="admin-grid">
          
          </div>
        </section>
      </div>
  )
}
