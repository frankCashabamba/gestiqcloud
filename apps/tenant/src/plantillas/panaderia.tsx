
import React, { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import SectorLayout from './components/SectorLayout'
import { useMisModulos } from '../hooks/useMisModulos'

function buildSlug(name?: string, url?: string, slug?: string): string {
  if (slug) return slug.toLowerCase()
  if (url) {
    const normalized = url.startsWith('/') ? url.slice(1) : url
    const segment = normalized.split('/')[0] || normalized
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
          to: `/mod/${buildSlug(m.nombre, m.url, m.slug)}`,
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
            </ul>
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
