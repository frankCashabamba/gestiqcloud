import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listImports, deleteImport, type HistImport } from '../services'
import PageContainer from '../../../components/PageContainer'

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
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState('')

  const load = () => {
    setLoading(true)
    listImports()
      .then(setImports)
      .catch(() => setImports([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteImport(deleteTarget)
      setDeleteTarget(null)
      setDeleteError('')
      load()
    } catch {
      setDeleteError('Error al eliminar la importacion')
    }
  }

  return (
    <PageContainer>
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
                      onClick={() => {
                        setDeleteTarget(imp.id)
                        setDeleteError('')
                      }}
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
      {deleteTarget && (
        <div style={modalBackdrop}>
          <div style={modalCard}>
            <h2 style={{ margin: '0 0 0.5rem', fontSize: 18 }}>Eliminar importacion</h2>
            <p style={{ color: '#475569', marginTop: 0 }}>
              Esta accion elimina la importacion historica y sus registros asociados.
            </p>
            {deleteError ? <div style={modalError}>{deleteError}</div> : null}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => {
                  setDeleteTarget(null)
                  setDeleteError('')
                }}
                style={modalCancelButton}
              >
                Cancelar
              </button>
              <button type="button" onClick={handleDelete} style={modalDeleteButton}>
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
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

const modalBackdrop: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 50,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'rgba(15, 23, 42, 0.45)',
  padding: '1rem',
}

const modalCard: React.CSSProperties = {
  width: '100%',
  maxWidth: 420,
  background: '#fff',
  borderRadius: 12,
  padding: '1.25rem',
  boxShadow: '0 18px 50px rgba(15, 23, 42, 0.25)',
}

const modalError: React.CSSProperties = {
  marginBottom: '0.75rem',
  padding: '0.6rem 0.75rem',
  border: '1px solid #fecaca',
  borderRadius: 8,
  background: '#fef2f2',
  color: '#991b1b',
  fontSize: 13,
}

const modalCancelButton: React.CSSProperties = {
  padding: '0.5rem 0.9rem',
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#fff',
  color: '#334155',
  cursor: 'pointer',
}

const modalDeleteButton: React.CSSProperties = {
  padding: '0.5rem 0.9rem',
  border: '1px solid #dc2626',
  borderRadius: 8,
  background: '#dc2626',
  color: '#fff',
  cursor: 'pointer',
}
