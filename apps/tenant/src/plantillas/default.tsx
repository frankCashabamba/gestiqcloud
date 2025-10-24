
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

const DefaultPlantilla: React.FC<{ slug?: string }> = ({ slug }) => {
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
      items.push(kpiCard('ventas', 'Ventas hoy', 'Conecta tu facturaci?n para ver datos en tiempo real.'))
    }
    if (allowedSlugs.has('gastos')) {
      items.push(kpiCard('gastos', 'Gastos del d?a', 'Carga comprobantes para monitorear el gasto operativo.'))
    }
    if (allowedSlugs.has('facturacion')) {
      items.push(kpiCard('facturacion', 'Facturas por cobrar', 'Revisa tus cuentas por cobrar y planifica la caja.'))
    }
    if (!items.length) {
      items.push(kpiCard('placeholder', 'KPIs pendientes', 'Activa indicadores desde Configuraci?n > Dashboards.'))
    }
    return items
  }, [allowedSlugs])

  const recommended = useMemo(() => sideNav.slice(0, 4), [sideNav])

  return (
    <SectorLayout
      title="Panel general"
      subtitle="Acceso r?pido a tus m?dulos habilitados y a los indicadores principales de la empresa."
      topNav={sideNav.slice(0, 3)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
        <section className="gc-card space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Bienvenido{slug ? ` ? ${slug}` : ''}</h2>
            <p className="mt-2 text-sm text-slate-500">
              Usa la navegaci?n lateral para abrir cada m?dulo o contin?a con los accesos sugeridos. Todo se sincroniza con tu tenant, por lo que los permisos y la informaci?n dependen de tu perfil.
            </p>
          </div>

          {quickAccess.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Accesos r?pidos</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {quickAccess.map((item) => (
                  <Link
                    key={item.to}
                    to={`${prefix}${item.to}`}
                    className="group flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
                  >
                    <span>{item.label}</span>
                    <span className="text-xs text-slate-400 transition group-hover:text-blue-600">Ver m?dulo ?</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 p-4">
            <h3 className="text-sm font-semibold text-slate-700">Personaliza tu tablero</h3>
            <p className="mt-2 text-sm text-slate-500">
              Desde Configuraci?n puedes decidir qu? KPIs muestran tus colaboradores, asignar plantillas por rol y definir los accesos por m?dulo.
            </p>
          </div>
        </section>

        <aside className="gc-card-muted space-y-4">
          <h3 className="text-sm font-semibold text-slate-700">Revisa tambi?n</h3>
          <ul className="space-y-3 text-sm text-slate-500">
            <li>? Configura la informaci?n de tu empresa para mostrar el branding en todas las pantallas.</li>
            <li>? Conecta tus cuentas bancarias o sube extractos para automatizar conciliaciones.</li>
            <li>? Define responsables por m?dulo para que reciban notificaciones y tareas pendientes.</li>
          </ul>

          {recommended.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">M?dulos destacados</h4>
              <div className="mt-3 space-y-2">
                {recommended.map((item) => (
                  <Link
                    key={item.to}
                    to={`${prefix}${item.to}`}
                    className="block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 transition hover:border-blue-200 hover:text-blue-700"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </SectorLayout>
  )
}

export default DefaultPlantilla
