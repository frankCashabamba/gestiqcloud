import React from 'react'
import SectorLayout from './components/SectorLayout'
import { useMisModulos } from '../hooks/useMisModulos'

const kpiBox: React.CSSProperties = { border: '1px solid var(--color-border)', background: 'var(--color-surface)', borderRadius: 12, padding: 12 }

const DefaultPlantilla: React.FC<{ slug?: string }> = ({ slug }) => {
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

  const has = (slug: string) => allowedSlugs.has(slug)

  const kpiBoxEl = (key: string, label: string) => (
    <div key={key} style={kpiBox}>{label}</div>
  )

  const kpis: React.ReactNode[] = []
  if (has('ventas')) kpis.push(kpiBoxEl('k1', 'Ventas hoy'))
  if (has('gastos')) kpis.push(kpiBoxEl('k2', 'Gastos hoy'))
  if (has('facturacion')) kpis.push(kpiBoxEl('k3', 'Facturas por cobrar'))
  if (has('contratos')) kpis.push(kpiBoxEl('k4', 'Contratos por vencer'))

  return (
    <SectorLayout
      title={`Plantilla: ${slug ?? 'default'}`}
      topNav={sideNav.slice(0, 2)}
      sideNav={sideNav}
      kpis={kpis}
    >
      <div style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)', borderRadius: 12, padding: 16 }}>
        Bienvenido. Usa la navegación lateral para acceder a los módulos.
      </div>
    </SectorLayout>
  )
}

export default DefaultPlantilla
