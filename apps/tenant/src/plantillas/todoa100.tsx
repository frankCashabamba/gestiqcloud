
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

const TodoA100Plantilla: React.FC<{ slug?: string }> = ({ slug }) => {
  const { modules, allowedSlugs } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''

  const sideNav = useMemo(
    () =>
      [...modules]
        .sort((a, b) => (a.nombre || '').localeCompare(b.nombre || ''))
        .map((m) => ({
          label: m.nombre || buildSlug(m.nombre, m.url, m.slug),
          // 'to' sin prefijo; SectorLayout aplica `${prefix}`
          to: `/${buildSlug(m.nombre, m.url, m.slug)}`,
        })),
    [modules]
  )

  const quickAccess = useMemo(() => sideNav.slice(0, 6), [sideNav])

  const kpis = useMemo(() => {
    const items: React.ReactNode[] = []
    if (allowedSlugs.has('ventas')) {
      items.push(kpiCard('ventas', 'Ventas por tienda', 'Compara sucursales y define objetivos diarios.'))
      items.push(kpiCard('ticket', 'Ticket promedio', 'Mide el valor de cada compra para ajustar promociones.'))
    }
    if (allowedSlugs.has('inventario')) {
      items.push(kpiCard('rotacion', 'Rotaci?n de stock', 'Identifica productos de alta y baja rotaci?n.'))
    }
    if (!items.length) {
      items.push(kpiCard('placeholder', 'KPIs personalizados', 'A?ade m?tricas de ventas y merchandising.'))
    }
    return items
  }, [allowedSlugs])

  return (
    <SectorLayout
      title="Sector Retail: Todo a 100"
      subtitle="Supervisa campa?as, stock y rentabilidad de tus tiendas f?sicas y digitales."
      topNav={sideNav.slice(0, 3)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
        <section className="gc-card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Plan comercial</h2>
            <p className="mt-2 text-sm text-slate-500">
              Organiza promociones, revisa m?rgenes por categor?a y coordina reposiciones con log?stica.
            </p>
          </div>

          {quickAccess.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Accesos recomendados</h3>
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
            <h3 className="text-sm font-semibold text-slate-700">Checklist diario</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-500">
              <li>? Actualizar precios y validar que las promociones est?n vigentes.</li>
              <li>? Revisar quiebres de stock en g?ndola y coordinar reposici?n.</li>
              <li>? Analizar productos destacados y planificar pushes comerciales.</li>
            </ul>
          </div>
        </section>

        <aside className="gc-card-muted space-y-4">
          <h3 className="text-sm font-semibold text-slate-700">Sugerencias</h3>
          <ul className="space-y-3 text-sm text-slate-500">
            <li>? Segmenta la base de clientes para campa?as espec?ficas.</li>
            <li>? Usa reportes de rotaci?n para decidir compras a proveedores.</li>
            <li>? Define objetivos de venta por turno para cada tienda.</li>
          </ul>
        </aside>
      </div>
    </SectorLayout>
  )
}

export default TodoA100Plantilla
