import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ImportUploader from '../components/ImportUploader'
import { fetchDashboard, type DashboardStats } from '../services'

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats>({
    total: 0,
    pendientes: 0,
    en_revision: 0,
    confirmados: 0,
    fallidos: 0,
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboard().then(setStats).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.35rem' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#6366f1', marginBottom: 6 }}>
            Importador
          </div>
          <h2 style={{ margin: 0, fontSize: 30, lineHeight: 1.1, color: '#0f172a' }}>Importador Contable Universal</h2>
          <p style={{ color: '#64748b', margin: '0.7rem 0 0', maxWidth: 760, fontSize: 16, lineHeight: 1.5 }}>
            Sube facturas, recibos, boletas en PDF, imagen, Excel, CSV, XML o TXT. El sistema clasifica y extrae datos automaticamente.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.55rem', padding: '0.35rem', border: '1px solid #e5e7eb', borderRadius: 16, background: 'rgba(255, 255, 255, 0.78)', backdropFilter: 'blur(10px)' }}>
          <button onClick={() => navigate('documents')} style={btn}>Ver Todos</button>
          <button onClick={() => navigate('recipes')} style={btn}>Recetas</button>
        </div>
      </div>
      {loading ? <p style={{ color: '#94a3b8', fontSize: 13, marginBottom: '1.25rem' }}>Cargando resumen...</p> : null}
      <div style={{ marginTop: '1.25rem' }}>
        <ImportUploader
          onImported={() => fetchDashboard().then(setStats).catch(() => {})}
          documentPathBuilder={(docId) => `documents/${docId}`}
        />
      </div>
    </div>
  )
}

const btn: React.CSSProperties = {
  padding: '0.62rem 1rem',
  border: '1px solid #d1d5db',
  borderRadius: 12,
  cursor: 'pointer',
  background: '#fff',
  fontSize: 14,
  fontWeight: 700,
  color: '#334155',
}
