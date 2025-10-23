import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useMisModulos } from '../hooks/useMisModulos'
import { useEffect, useState } from 'react'
import { getMiEmpresa, type Empresa } from '../services/empresa'

export default function Dashboard() {
  const { logout, brand, profile } = useAuth()
  const { modules, loading, error } = useMisModulos()
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  const [empresaInfo, setEmpresaInfo] = useState<Empresa | null>(null)
  useEffect(() => { getMiEmpresa().then(arr => setEmpresaInfo(arr[0] || null)).catch(()=>{}) }, [])
  return (
    <div>
      {/* Header general con Inicio/Cerrar sesión está en TenantShell */}
      <div style={{ maxWidth: 960, margin: '0 auto 1rem', color: 'var(--color-muted)', fontSize: 14, display: 'flex', gap: 16 }}>
        <span>Empresa: <strong>{empresaInfo?.nombre || empresa || '—'}</strong></span>
        <span>Usuario: <strong>{profile?.username || profile?.user_id || '—'}</strong></span>
      </div>
      <div style={{ maxWidth: 960, margin: '1rem auto' }}>
        <h3 style={{ marginTop: 0 }}>Módulos contratados {(!loading && modules.length > 0) ? `(${modules.length})` : ''}</h3>
        {loading && <div style={{ color: 'var(--color-muted)' }}>Cargando módulos…</div>}
        {!loading && modules.length === 0 && (
          <div style={{ color: 'var(--color-muted)' }}>No hay módulos contratados para esta empresa.</div>
        )}
        {!loading && modules.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
          {[...modules].sort((a,b) => (a.nombre || '').localeCompare(b.nombre || '')).map((m) => {
            const normalizedUrl = m.url ? m.url.replace(/^\/mod/, '').replace(new RegExp(`^\/${empresa || ''}`), '') : `/${(m.nombre || '').toLowerCase()}`
            const to = prefix + normalizedUrl
            return (
              <Link key={m.id} to={to} style={{ display: 'block', padding: 16, border: '1px solid var(--color-border)', borderRadius: 12, background: 'var(--color-surface)', textDecoration: 'none', color: 'inherit' }}>
                <div style={{ fontWeight: 600 }}>{m.nombre}</div>
                <div style={{ color: 'var(--color-muted)', fontSize: 13 }}>{m.categoria || 'Módulo'}</div>
              </Link>
            )
          })}
          </div>
        )}
      </div>
    </div>
  )
}


