
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

const TallerPlantilla: React.FC<{ slug?: string }> = ({ slug }) => {
  const { modules, allowedSlugs } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''

  const sideNav = useMemo(
    () =>
      [...modules]
        .sort((a, b) => (a.nombre || '').localeCompare(b.nombre || ''))
        .map((m) => ({
          label: m.nombre || buildSlug(m.nombre, m.url, m.slug),
          // 'to' relativo; el prefijo del tenant se añade al renderizar
          to: `/${buildSlug(m.nombre, m.url, m.slug)}`,
        })),
    [modules]
  )

  const quickAccess = useMemo(() => sideNav.slice(0, 6), [sideNav])

  const kpis = useMemo(() => {
    const items: React.ReactNode[] = []
    if (allowedSlugs.has('facturacion')) {
      items.push(kpiCard('ordenes', '?rdenes abiertas', 'Controla ?rdenes de trabajo planificadas y en curso.'))
      items.push(kpiCard('facturacion', 'Facturas pendientes', 'Genera facturas apenas cierres las intervenciones.'))
    }
    if (allowedSlugs.has('rrhh')) {
      items.push(kpiCard('rrhh', 'Utilizaci?n de t?cnicos', 'Mide la ocupaci?n de tu personal especializado.'))
    }
    if (!items.length) {
      items.push(kpiCard('placeholder', 'KPIs por configurar', 'A?ade m?tricas de productividad y facturaci?n.'))
    }
    return items
  }, [allowedSlugs])

  return (
    <SectorLayout
      title="Sector Taller"
      subtitle="Gestiona ?rdenes de trabajo, repuestos y tiempos de servicio desde un solo lugar."
      topNav={sideNav.slice(0, 3)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
        <section className="gc-card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Agenda del d?a</h2>
            <p className="mt-2 text-sm text-slate-500">
              Registra check-in y diagn?stico, asigna t?cnicos y da seguimiento a los repuestos solicitados.
            </p>
          </div>

          {quickAccess.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Accesos frecuentes</h3>
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
              <li>? Revisar ?rdenes pr?ximas a vencer y comunicar avances al cliente.</li>
              <li>? Validar disponibilidad de repuestos y actualizar inventario.</li>
              <li>? Registrar tiempos reales para medir eficiencia por t?cnico.</li>
            </ul>
          </div>
        </section>

        <aside className="gc-card-muted space-y-4">
          <h3 className="text-sm font-semibold text-slate-700">Recomendaciones</h3>
          <ul className="space-y-3 text-sm text-slate-500">
            <li>? Define plantillas de checklists por tipo de servicio.</li>
            <li>? Utiliza fotograf?as del antes y despu?s para documentar trabajos.</li>
            <li>? Activa recordatorios autom?ticos de mantenimiento para clientes recurrentes.</li>
          </ul>
        </aside>
      </div>
    </SectorLayout>
  )
}

export default TallerPlantilla
