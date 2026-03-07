import React from 'react'

import { Routes, Route, Navigate } from 'react-router-dom'

import CategoriaGastoForm from './categorias-gasto/CategoriaGastoForm'
import CategoriaGastoList from './categorias-gasto/CategoriaGastoList'
import FieldConfigManager from './FieldConfigManager'
import ImportCatalog from './ImportCatalog'
import HorarioForm from './horarios/HorarioForm'
import HorarioList from './horarios/HorarioList'
import IdiomaForm from './idiomas/IdiomaForm'
import IdiomaList from './idiomas/IdiomaList'
import LocaleForm from './locales/LocaleForm'
import LocaleList from './locales/LocaleList'
import MonedaForm from './monedas/MonedaForm'
import MonedaList from './monedas/MonedaList'
import PaisList from './paises/PaisList'
import PermisosList from './permisos/PermisosList'
import SectorForm from './sectores/SectorForm'
import SectorList from './sectores/SectorList'
import TimezoneForm from './timezones/TimezoneForm'
import TimezoneList from './timezones/TimezoneList'
import PaisForm from './paises/PaisForm'
import TipoEmpresaForm from './tipo-empresa/TipoEmpresaForm'
import TipoEmpresaList from './tipo-empresa/TipoEmpresaList'
import TipoNegocioForm from './tipo-negocio/TipoNegocioForm'
import TipoNegocioList from './tipo-negocio/TipoNegocioList'
import PermisoForm from './permisos/PermisoForm'
import TipoDocumentoForm from './tipos-documento/TipoDocumentoForm'
import TipoDocumentoList from './tipos-documento/TipoDocumentoList'
import TipoIdentificacionForm from './tipos-identificacion/TipoIdentificacionForm'
import TipoIdentificacionList from './tipos-identificacion/TipoIdentificacionList'
import TipoImpuestoForm from './tipos-impuesto/TipoImpuestoForm'
import TipoImpuestoList from './tipos-impuesto/TipoImpuestoList'
import UnidadMedidaForm from './unidades-medida/UnidadMedidaForm'
import UnidadMedidaList from './unidades-medida/UnidadMedidaList'
import MetodoPagoList from './metodos-pago/MetodoPagoList'
import MetodoPagoForm from './metodos-pago/MetodoPagoForm'
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
        <h2>Fiscal y contable</h2>
        <div className="admin-grid">
          <AdminCard
            href="tipos-impuesto"
            iconSrc="/icons/configuracion.jpeg"
            title="Tipos de impuesto"
            description="Gestiona los tipos de impuesto por país (IVA, IGIC, etc.)."
            iconSize="sm"
          />
          <AdminCard
            href="metodos-pago"
            iconSrc="/icons/configuracion.jpeg"
            title="Métodos de pago"
            description="Catálogo global de métodos de pago disponibles."
            iconSize="sm"
          />
          <AdminCard
            href="categorias-gasto"
            iconSrc="/icons/configuracion.jpeg"
            title="Categorías de gasto"
            description="Gestiona la jerarquía de categorías para gastos."
            iconSize="sm"
          />
          <AdminCard
            href="tipos-documento"
            iconSrc="/icons/configuracion.jpeg"
            title="Tipos de documento"
            description="Catálogo de tipos de documento (factura, recibo, etc.)."
            iconSize="sm"
          />
          <AdminCard
            href="unidades-medida"
            iconSrc="/icons/configuracion.jpeg"
            title="Unidades de medida"
            description="Gestiona las unidades de medida disponibles (kg, lb, etc.)."
            iconSize="sm"
          />
          <AdminCard
            href="tipos-identificacion"
            iconSrc="/icons/configuracion.jpeg"
            title="Tipos de identificación"
            description="Catálogo global de tipos de documento de identidad por país (CEDULA, RUC, DNI, etc.)."
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
            href="/admin/modules"
            iconSrc="/icons/configuracion.jpeg"
            title="Módulos"
            description="Alta, edición y configuración de módulos del sistema."
            iconSize="sm"
          />
          <AdminCard
            href="fields"
            iconSrc="/icons/configuracion.jpeg"
            title="Campos (global/tenant)"
            description="Catálogo de campos por módulo (incluye imports_*)."
            iconSize="sm"
          />
          <AdminCard
            href="imports-catalog"
            iconSrc="/icons/configuracion.jpeg"
            title="Importar catálogos"
            description="Trae campos desde tablas permitidas para imports."
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
      <Route path="tipos-impuesto" element={<TipoImpuestoList />} />
      <Route path="tipos-impuesto/nuevo" element={<TipoImpuestoForm />} />
      <Route path="tipos-impuesto/:id/editar" element={<TipoImpuestoForm />} />
      <Route path="tipos-identificacion" element={<TipoIdentificacionList />} />
      <Route path="tipos-identificacion/nuevo" element={<TipoIdentificacionForm />} />
      <Route path="tipos-identificacion/:id/editar" element={<TipoIdentificacionForm />} />
      <Route path="unidades-medida" element={<UnidadMedidaList />} />
      <Route path="unidades-medida/nuevo" element={<UnidadMedidaForm />} />
      <Route path="unidades-medida/:id/editar" element={<UnidadMedidaForm />} />
      <Route path="tipos-documento" element={<TipoDocumentoList />} />
      <Route path="tipos-documento/nuevo" element={<TipoDocumentoForm />} />
      <Route path="tipos-documento/:id/editar" element={<TipoDocumentoForm />} />
      <Route path="categorias-gasto" element={<CategoriaGastoList />} />
      <Route path="categorias-gasto/nuevo" element={<CategoriaGastoForm />} />
      <Route path="categorias-gasto/:id/editar" element={<CategoriaGastoForm />} />
      <Route path="metodos-pago" element={<MetodoPagoList />} />
      <Route path="metodos-pago/nuevo" element={<MetodoPagoForm />} />
      <Route path="metodos-pago/:id/editar" element={<MetodoPagoForm />} />
      <Route path="fields" element={<FieldConfigManager />} />
      <Route path="imports-catalog" element={<ImportCatalog />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
