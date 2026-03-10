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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Importador Contable Universal</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={() => navigate('documents')} style={btn}>Ver Todos</button>
          <button onClick={() => navigate('recipes')} style={btn}>Recetas</button>
        </div>
      </div>
      <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
        Sube facturas, recibos, boletas en PDF, imagen, Excel, CSV, XML o TXT. El sistema clasifica y extrae datos automaticamente.
      </p>
      {loading ? <p>Cargando...</p> : (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <StatCard label="Total Documentos" value={stats.total} color="#374151" />
          <StatCard label="Pendientes" value={stats.pendientes} color="#F59E0B" />
          <StatCard label="En Revision" value={stats.en_revision} color="#3B82F6" onClick={() => navigate('documents?estado=REVIEW')} />
          <StatCard label="Confirmados" value={stats.confirmados} color="#10B981" />
          <StatCard label="Fallidos" value={stats.fallidos} color="#EF4444" />
        </div>
      )}
      <div style={{ marginTop: '2rem' }}>
        <ImportUploader
          onImported={() => fetchDashboard().then(setStats).catch(() => {})}
          documentPathBuilder={(docId) => `documents/${docId}`}
        />
      </div>
    </div>
  )
}

function StatCard({ label, value, color, onClick }: { label: string; value: number; color: string; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: 12,
        padding: '1.25rem',
        background: '#fff',
        minWidth: 160,
        flex: 1,
        cursor: onClick ? 'pointer' : 'default',
        borderLeft: `4px solid ${color}`,
      }}
    >
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4 }}>{label}</div>
    </div>
  )
}

const btn: React.CSSProperties = {
  padding: '0.5rem 1rem',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  cursor: 'pointer',
  background: '#fff',
  fontSize: 14,
}
