import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ImportUploader from '../components/ImportUploader'
import { fetchDashboard, type DashboardStats } from '../services'

const EMPTY_STATS: DashboardStats = {
  total: 0,
  pendientes: 0,
  en_revision: 0,
  confirmados: 0,
  fallidos: 0,
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS)
  const [loading, setLoading] = useState(true)

  const loadDashboard = async () => {
    try {
      setStats(await fetchDashboard())
    } catch {
      setStats(EMPTY_STATS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDashboard()
  }, [])

  return (
    <>
      <style>{`
        @media (max-width: 960px) {
          .importador-dashboard__hero {
            padding: 1.1rem !important;
          }
          .importador-dashboard__stats {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
        }

        @media (max-width: 640px) {
          .importador-dashboard {
            padding: 1rem !important;
          }
          .importador-dashboard__hero {
            padding: 1rem !important;
          }
          .importador-dashboard__actions {
            width: 100%;
          }
          .importador-dashboard__actions button {
            flex: 1;
          }
          .importador-dashboard__stats {
            grid-template-columns: minmax(0, 1fr) !important;
          }
        }
      `}</style>

      <div className="importador-dashboard" style={{ padding: '1.5rem', display: 'grid', gap: '1rem' }}>
        <section
          className="importador-dashboard__hero"
          style={{
            borderRadius: 30,
            padding: '1.35rem',
            background: 'linear-gradient(135deg, #fffdf8 0%, #eef6ff 52%, #ffffff 100%)',
            border: '1px solid #e2e8f0',
            boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div style={{ maxWidth: 760 }}>
              <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#0f766e', marginBottom: 6 }}>
                Modulo importador
              </div>
              <h1 style={{ margin: 0, fontSize: 32, lineHeight: 1.05, color: '#0f172a' }}>Central de documentos</h1>
              <p style={{ margin: '0.6rem 0 0', fontSize: 15, color: '#475569', maxWidth: 700 }}>
                Sube archivos, revisa la informacion detectada y guarda cada documento en su destino. Todo el flujo queda concentrado en una sola bandeja.
              </p>
              <p style={{ margin: '0.55rem 0 0', fontSize: 13, color: '#0f766e', maxWidth: 700, fontWeight: 700 }}>
                El importador aprende de los documentos que validas. No hace falta elegir plantillas manuales para el flujo normal.
              </p>
            </div>
            <div className="importador-dashboard__actions" style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <button onClick={() => navigate('documents')} style={primaryBtn}>Ir a documentos</button>
              <button onClick={() => navigate('upload')} style={secondaryBtn}>Nueva importacion</button>
            </div>
          </div>

          <div
            className="importador-dashboard__stats"
            style={{
              marginTop: '1rem',
              display: 'grid',
              gridTemplateColumns: 'repeat(5, minmax(0, 1fr))',
              gap: '0.8rem',
            }}
          >
            {[
              { label: 'Total', value: stats.total, note: 'Documentos registrados', tone: '#334155', bg: '#e2e8f0' },
              { label: 'Pendientes', value: stats.pendientes, note: 'Aun no procesados', tone: '#92400e', bg: '#fef3c7' },
              { label: 'Por revisar', value: stats.en_revision, note: 'Requieren validacion', tone: '#1d4ed8', bg: '#dbeafe' },
              { label: 'Confirmados', value: stats.confirmados, note: 'Listos para guardarse', tone: '#166534', bg: '#dcfce7' },
              { label: 'Con error', value: stats.fallidos, note: 'Necesitan correccion', tone: '#991b1b', bg: '#fee2e2' },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  padding: '0.95rem 1rem',
                  borderRadius: 18,
                  background: '#fff',
                  border: '1px solid rgba(148, 163, 184, 0.16)',
                }}
              >
                <div style={{ display: 'inline-flex', padding: '0.22rem 0.55rem', borderRadius: 999, background: item.bg, color: item.tone, fontSize: 11, fontWeight: 800 }}>
                  {item.label}
                </div>
                <div style={{ marginTop: 10, fontSize: 28, fontWeight: 800, color: '#0f172a' }}>
                  {loading ? '...' : item.value}
                </div>
                <div style={{ marginTop: 4, fontSize: 12, color: '#64748b' }}>{item.note}</div>
              </div>
            ))}
          </div>
        </section>

        <section
          style={{
            borderRadius: 24,
            border: '1px solid #e2e8f0',
            background: '#fff',
            boxShadow: '0 18px 36px rgba(15, 23, 42, 0.05)',
            padding: '1rem',
          }}
        >
          <div style={{ marginBottom: '0.9rem' }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Nueva importacion</div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
              Carga aqui nuevos archivos. Cuando termine el procesamiento podras abrir cada documento y revisar los datos detectados.
            </div>
          </div>
          <ImportUploader
            onImported={() => { void loadDashboard() }}
            documentPathBuilder={(docId) => `documents/${docId}`}
          />
        </section>
      </div>
    </>
  )
}

const primaryBtn: React.CSSProperties = {
  padding: '0.8rem 1rem',
  border: 'none',
  borderRadius: 14,
  cursor: 'pointer',
  background: 'linear-gradient(135deg, #0f766e 0%, #0d9488 100%)',
  color: '#fff',
  fontSize: 14,
  fontWeight: 800,
  boxShadow: '0 14px 28px rgba(13, 148, 136, 0.22)',
}

const secondaryBtn: React.CSSProperties = {
  padding: '0.8rem 1rem',
  border: '1px solid #cbd5e1',
  borderRadius: 14,
  cursor: 'pointer',
  background: '#fff',
  color: '#334155',
  fontSize: 14,
  fontWeight: 800,
}
