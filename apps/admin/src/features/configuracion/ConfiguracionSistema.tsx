import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import MonedaList from './monedas/MonedaList'
import MonedaForm from './monedas/MonedaForm'
import IdiomaList from './idiomas/IdiomaList'
import IdiomaForm from './idiomas/IdiomaForm'
import LocaleList from './locales/LocaleList'
import LocaleForm from './locales/LocaleForm'
import TimezoneList from './timezones/TimezoneList'
import TimezoneForm from './timezones/TimezoneForm'
import SectorList from './sectores/SectorList'
import SectorForm from './sectores/SectorForm'
import PaisList from './paises/PaisList'
import PaisForm from './paises/PaisForm'
import TipoEmpresaList from './tipo-empresa/TipoEmpresaList'
import TipoEmpresaForm from './tipo-empresa/TipoEmpresaForm'
import TipoNegocioList from './tipo-negocio/TipoNegocioList'
import TipoNegocioForm from './tipo-negocio/TipoNegocioForm'
import HorarioList from './horarios/HorarioList'
import HorarioForm from './horarios/HorarioForm'
import PermisosList from './permisos/PermisosList'
import PermisoForm from './permisos/PermisoForm'
import { AdminCard } from '../../components/AdminCard'
import '../../pages/admin-panel.css'
import RolesRouter from './roles/RolesRouter'

function Index() {
  return (
    <div className="admin-container">
      <header>
        <h1 className="admin-title">Configuración del sistema</h1>
        <p style={{ color: '#4b5563', margin: 0 }}>Selecciona una sección para comenzar.</p>
      </header>

      <section className="admin-section">
        <h2>Empresa</h2>
        <div className="admin-grid">
          <AdminCard
            href="tipo-empresa"
            iconSrc="/icons/empresas.png"
            title="Tipos de empresa"
            description="Gestiona las categorías/tipos disponibles para nuevas empresas."
            iconSize="sm"
          />
          <AdminCard
            href="tipo-negocio"
            iconSrc="/icons/empresas.png"
            title="Tipos de negocio"
            description="Gestiona los tipos de negocio disponibles."
            iconSize="sm"
          />
          <AdminCard
            href="sectores"
            iconSrc="/icons/empresas.png"
            title="Sectores plantilla"
            description="Configura sectores y estructuras base para empresas."
            iconSize="sm"
          />
          <AdminCard
            href="horarios"
            iconSrc="/icons/usuario.png"
            title="Horarios de atención"
            description="Define días y rangos de horas de funcionamiento."
            iconSize="sm"
          />
        </div>
      </section>

      <section className="admin-section">
        <h2>Internacionalización</h2>
        <div className="admin-grid">
          <AdminCard
            href="idiomas"
            iconSrc="/icons/usuario.png"
            title="Idiomas"
            description="Gestiona los idiomas disponibles en el sistema."
            iconSize="sm"
          />
          <AdminCard
            href="monedas"
            iconSrc="/icons/usuario.png"
            title="Monedas"
            description="Define las monedas permitidas para operaciones."
            iconSize="sm"
          />
          <AdminCard
            href="paises"
            iconSrc="/icons/configuracion.jpeg"
            title="Paises"
            description="Gestiona el catalogo de paises disponibles."
            iconSize="sm"
          />
          <AdminCard
            href="locales"
            iconSrc="/icons/configuracion.jpeg"
            title="Locales"
            description="Gestiona los locales/idiomas del sistema."
            iconSize="sm"
          />
          <AdminCard
            href="timezones"
            iconSrc="/icons/configuracion.jpeg"
            title="Zonas horarias"
            description="Gestiona el catalogo de zonas horarias."
            iconSize="sm"
          />
        </div>
      </section>

      <section className="admin-section">
        <h2>Seguridad</h2>
        <div className="admin-grid">
          <AdminCard
            href="roles"
            iconSrc="/icons/usuario.png"
            title="Roles base"
            description="Gestiona los roles y permisos predeterminados."
            iconSize="sm"
          />
          <AdminCard
            href="permisos"
            iconSrc="/icons/configuracion.jpeg"
            title="Permisos globales"
            description="Gestiona el catálogo global de permisos por módulo."
            iconSize="sm"
          />
          <AdminCard
            href="/admin/modulos"
            iconSrc="/icons/configuracion.jpeg"
            title="Módulos"
            description="Alta, edición y configuración de módulos del sistema."
            iconSize="sm"
          />
        </div>
      </section>
    </div>
  )
}

export default function ConfiguracionSistema() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="idiomas" element={<IdiomaList />} />
      <Route path="idiomas/nuevo" element={<IdiomaForm />} />
      <Route path="idiomas/:id/editar" element={<IdiomaForm />} />
      <Route path="monedas" element={<MonedaList />} />
      <Route path="monedas/nuevo" element={<MonedaForm />} />
      <Route path="monedas/:id/editar" element={<MonedaForm />} />
      <Route path="paises" element={<PaisList />} />
      <Route path="paises/nuevo" element={<PaisForm />} />
      <Route path="paises/:id/editar" element={<PaisForm />} />
      <Route path="locales" element={<LocaleList />} />
      <Route path="locales/nuevo" element={<LocaleForm />} />
      <Route path="locales/:id/editar" element={<LocaleForm />} />
      <Route path="timezones" element={<TimezoneList />} />
      <Route path="timezones/nuevo" element={<TimezoneForm />} />
      <Route path="timezones/:id/editar" element={<TimezoneForm />} />
      <Route path="sectores" element={<SectorList />} />
      <Route path="sectores/nuevo" element={<SectorForm />} />
      <Route path="sectores/:id/editar" element={<SectorForm />} />
      <Route path="tipo-empresa" element={<TipoEmpresaList />} />
      <Route path="tipo-empresa/nuevo" element={<TipoEmpresaForm />} />
      <Route path="tipo-empresa/:id/editar" element={<TipoEmpresaForm />} />
      <Route path="tipo-negocio" element={<TipoNegocioList />} />
      <Route path="tipo-negocio/nuevo" element={<TipoNegocioForm />} />
      <Route path="tipo-negocio/:id/editar" element={<TipoNegocioForm />} />
      <Route path="roles/*" element={<RolesRouter />} />
      <Route path="permisos" element={<PermisosList />} />
      <Route path="permisos/nuevo" element={<PermisoForm />} />
      <Route path="permisos/:id/editar" element={<PermisoForm />} />
      <Route path="horarios" element={<HorarioList />} />
      <Route path="horarios/nuevo" element={<HorarioForm />} />
      <Route path="horarios/:id/editar" element={<HorarioForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
