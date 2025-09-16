import React from 'react'
import SectorLayout from './components/SectorLayout'
import { useMisModulos } from '../hooks/useMisModulos'

const kpiBox: React.CSSProperties = { border: '1px solid var(--color-border)', background: 'var(--color-surface)', borderRadius: 12, padding: 12 }

const TallerPlantilla: React.FC<{ slug?: string }> = ({ slug }) => {
  const { modules, allowedSlugs } = useMisModulos()
  const toSlug = (name?: string, url?: string, slug?: string) => {
    if (slug) return slug.toLowerCase()
    if (url) {
      const u = url.startsWith('/') ? url.slice(1) : url
      return (u.split('/')[0] || u).toLowerCase()
    }
    return (name || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '')
  }
  const sideNav = [...modules]
    .sort((a,b) => (a.nombre || '').localeCompare(b.nombre || ''))
    .map(m => ({ label: m.nombre || toSlug(m.nombre, m.url, m.slug), to: `/mod/${toSlug(m.nombre, m.url, m.slug)}` }))
  const has = (s: string) => allowedSlugs.has(s)
  const kpi = (key: string, label: string) => <div key={key} style={kpiBox}>{label}</div>
  const kpis: React.ReactNode[] = []
  if (has('facturacion')) { kpis.push(kpi('k1', 'Órdenes hoy')); kpis.push(kpi('k3', 'Facturas pendientes')) }
  if (has('rrhh')) { kpis.push(kpi('k4', 'Utilización')) }
  if (kpis.length === 0) { kpis.push(kpi('k0', 'KPIs no disponibles')) }

  return (
    <SectorLayout
      title="Sector Taller"
      topNav={sideNav.slice(0, 2)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)', borderRadius: 12, padding: 16 }}>
        Plantilla de sector para “{slug ?? 'taller'}”. Ajusta módulos y KPIs específicos.
      </div>
    </SectorLayout>
  )
}

export default TallerPlantilla
