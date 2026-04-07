import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listImports, deleteImport, type HistImport } from '../services'

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  completed: { label: 'Completado', color: '#166534', bg: '#dcfce7' },
  processing: { label: 'Procesando', color: '#7c3aed', bg: '#ede9fe' },
  pending: { label: 'Pendiente', color: '#92400e', bg: '#fef3c7' },
  failed: { label: 'Error', color: '#991b1b', bg: '#fee2e2' },
  partial: { label: 'Parcial', color: '#1d4ed8', bg: '#dbeafe' },
}

function statusBadge(status: string) {
  const meta = STATUS_META[status] || { label: status, color: '#334155', bg: '#e2e8f0' }
  return (
    <span
      style={{
        background: meta.bg,
        color: meta.color,
        padding: '0.25rem 0.6rem',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {meta.label}
    </span>
  )
}

export default function ImportsPage() {
  const navigate = useNavigate()
  const [imports, setImports] = useState<HistImport[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    listImports()
      .then(setImports)
      .catch(() => setImports([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar esta importación y todos sus registros?')) return
    try {
      await deleteImport(id)
      load()
    } catch {
      alert('Error al eliminar la importación')
    }
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h1 style={{ margin: 0, fontSize: 24, color: '#0f172a' }}>Importaciones históricas</h1>
        <button
          onClick={() => navigate('../upload')}
          style={{
            padding: '0.6rem 1.2rem',
            border: 'none',
            borderRadius: 12,
            cursor: 'pointer',
            background: 'linear-gradient(135deg, #7c3aed 0%, #8B5CF6 100%)',
            color: '#fff',
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          Subir archivo
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '2rem', color: '#64748b' }}>Cargando...</div>
      ) : imports.length === 0 ? (
        <div style={{ padding: '2rem', color: '#64748b', textAlign: 'center' }}>
          No hay importaciones. Sube un archivo para comenzar.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                <th style={th}>Archivo</th>
                <th style={th}>Tipo</th>
                <th style={th}>Estado</th>
                <th style={th}>Filas</th>
                <th style={th}>Importadas</th>
                <th style={th}>Errores</th>
                <th style={th}>Fecha</th>
                <th style={th}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((imp) => (
                <tr key={imp.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={td}>{imp.filename}</td>
                  <td style={td}>{imp.import_type}</td>
                  <td style={td}>{statusBadge(imp.status)}</td>
                  <td style={tdNum}>{imp.total_rows}</td>
                  <td style={tdNum}>{imp.imported_rows}</td>
                  <td style={tdNum}>{imp.failed_rows}</td>
                  <td style={td}>{imp.created_at?.slice(0, 10)}</td>
                  <td style={td}>
                    <button
                      onClick={() => handleDelete(imp.id)}
                      style={{
                        padding: '0.3rem 0.6rem',
                        border: '1px solid #fca5a5',
                        borderRadius: 8,
                        cursor: 'pointer',
                        background: '#fff',
                        color: '#dc2626',
                        fontSize: 12,
                        fontWeight: 600,
                      }}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const th: React.CSSProperties = {
  textAlign: 'left',
  padding: '0.6rem 0.75rem',
  color: '#64748b',
  fontWeight: 700,
  fontSize: 12,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const td: React.CSSProperties = {
  padding: '0.6rem 0.75rem',
  color: '#0f172a',
}

const tdNum: React.CSSProperties = {
  ...td,
  textAlign: 'right',
  fontVariantNumeric: 'tabular-nums',
}
