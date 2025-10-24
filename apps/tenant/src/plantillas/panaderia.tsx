/**
 * Plantilla Panadería - Dashboard Principal
 * Adaptable según plan contratado (basic, standard, professional)
 */

import React, { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import SectorLayout from './components/SectorLayout'
import { useMisModulos } from '../hooks/useMisModulos'

function buildSlug(name?: string, url?: string, slug?: string): string {
  if (slug) return slug.toLowerCase()
  if (url) {
    let normalized = url.startsWith('/') ? url.slice(1) : url
    // Quita prefijo /mod si existe (legacy)
    if (normalized.startsWith('mod/')) normalized = normalized.slice(4)
    const parts = normalized.split('/').filter(p => p)
    const segment = parts[parts.length - 1] || normalized
    return segment.toLowerCase()
  }
  return (name || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, '')
}

const kpiCard = (key: string, title: string, helper: string) => (
  <article key={key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
    <p className="mt-3 text-2xl font-semibold text-slate-900">--</p>
    <p className="mt-2 text-[11px] text-slate-400">{helper}</p>
  </article>
)

const PanaderiaPlantilla: React.FC<{ slug?: string }> = ({ slug }) => {
  const { modules, allowedSlugs } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''

  const sideNav = useMemo(
    () =>
      [...modules]
        .sort((a, b) => (a.nombre || '').localeCompare(b.nombre || ''))
        .map((m) => ({
          label: m.nombre || buildSlug(m.nombre, m.url, m.slug),
          // 'to' debe ser solo el segmento del módulo
          to: `/${buildSlug(m.nombre, m.url, m.slug)}`,
        })),
    [modules]
  )

  const quickAccess = useMemo(() => sideNav.slice(0, 6), [sideNav])

  const kpis = useMemo(() => {
    const items: React.ReactNode[] = []
    if (allowedSlugs.has('ventas')) {
      items.push(kpiCard('ventas', 'Ventas mostrador', 'Integra la caja para conocer el ingreso diario.'))
    }
    if (allowedSlugs.has('inventario')) {
      items.push(kpiCard('inventario', 'Stock cr?tico', 'Controla ingredientes clave y evita quiebres.'))
    }
    if (allowedSlugs.has('gastos')) {
      items.push(kpiCard('gastos', 'Mermas registradas', 'Registra mermas y ajustes desde el m?dulo de inventario.'))
    }
    if (!items.length) {
      items.push(kpiCard('placeholder', 'KPIs en configuraci?n', 'Personaliza indicadores para tu panader?a.'))
    }
    return items
  }, [allowedSlugs])

  return (
    <SectorLayout
      title="Sector Panader?a"
      subtitle="Controla la producci?n diaria, el inventario de materias primas y las ventas en sal?n."
      topNav={sideNav.slice(0, 3)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
        <section className="gc-card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Agenda operativa</h2>
            <p className="mt-2 text-sm text-slate-500">
              Revisa los pedidos programados, coordina la producci?n en turnos y mant?n la trazabilidad de insumos frescos.
            </p>
          </div>

          {quickAccess.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Accesos clave</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {quickAccess.map((item) => (
                  <Link
                    key={item.to}
                    to={`${prefix}${item.to}`}
                    className="group flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
                  >
                    <span>{item.label}</span>
                    <span className="text-xs text-slate-400 transition group-hover:text-blue-600">Abrir ?</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 p-4">
          <h3 className="text-sm font-semibold text-slate-700">Checklist sugerido</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-500">
          <li>? Registrar la producci?n del d?a y validar los lotes pendientes.</li>
          <li>? Actualizar mermas y ajustes de inventario antes del cierre.</li>
          <li>? Revisar ventas por canal (sal?n, delivery y preventa corporativa).</li>
            <li>? Importar diario de producci?n desde Excel para digitalizar registros.</li>
            </ul>
          </div>

          {/* Importación de Datos - BÁSICO para todos */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Importar Datos</h3>
                <p className="mt-2 text-sm text-slate-500">
                  Digitaliza tu información existente desde archivos Excel o CSV.
                </p>
              </div>
              <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <a
                href="/api/v1/import-products"
                onClick={(e) => {
                  e.preventDefault()
                  // Abrir modal de importación (implementar después)
                  alert('Funcionalidad de importación: Sube tu archivo Excel/CSV con columnas PRODUCTO, CANTIDAD, PRECIO')
                }}
                className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-blue-300 hover:bg-blue-50 cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <svg className="h-5 w-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" />
                    <path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                  </svg>
                  <span className="font-medium text-slate-900">Productos (Excel/CSV)</span>
                </div>
                <p className="text-xs text-slate-500">
                  Importa catálogo completo: productos, stock y precios
                </p>
                <span className="text-xs text-blue-600 font-medium">→ Usar importador genérico</span>
              </a>

              {allowedSlugs.has('inventario') && (
                <Link
                  to={`${prefix}/panaderia/importador`}
                  className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-blue-300 hover:bg-blue-50"
                >
                  <div className="flex items-center gap-2">
                    <svg className="h-5 w-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium text-slate-900">Diario de Producción</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Importa registros históricos de producción diaria (SPEC-1)
                  </p>
                  <span className="text-xs text-amber-600 font-medium">→ Formato panadería avanzado</span>
                </Link>
              )}
            </div>

            <div className="mt-4 rounded-lg bg-blue-50 p-3">
              <div className="flex items-start gap-2">
                <svg className="h-5 w-5 flex-shrink-0 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <p className="text-xs text-blue-800">
                  <strong>Formatos soportados:</strong> Excel (.xlsx, .xls), CSV (.csv). 
                  Máximo 5,000 filas por importación.
                </p>
              </div>
            </div>
          </div>
        </section>

        <aside className="gc-card-muted space-y-4">
          <h3 className="text-sm font-semibold text-slate-700">Tips de configuraci?n</h3>
          <ul className="space-y-3 text-sm text-slate-500">
            <li>? Activa alertas de stock bajo para manteca, harina y levadura.</li>
            <li>? Usa recetas est?ndar para calcular costes y rentabilidad.</li>
            <li>? Programa turnos y controla asistencia desde RRHH.</li>
          </ul>
        </aside>
      </div>
    </SectorLayout>
  )
}

export default PanaderiaPlantilla
