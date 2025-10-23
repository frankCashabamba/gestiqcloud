import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useFichajes } from './hooks/useFichajes'

export default function FichajesView() {
  const navigate = useNavigate()
  const { fichajes, loading } = useFichajes()

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        <button
          onClick={() => navigate(-1)}
          style={{ marginRight: 16, padding: '8px 12px', background: '#6b7280', color: 'white', border: 'none', borderRadius: 4 }}
        >
          ← Volver
        </button>
        <h2 style={{ fontWeight: 700, fontSize: 18 }}>Fichajes</h2>
      </div>
      {loading ? (
        <div>Cargando…</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
            <thead style={{ background: '#f3f4f6' }}>
              <tr>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Fecha</th>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Entrada</th>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Salida</th>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Tipo</th>
              </tr>
            </thead>
            <tbody>
              {fichajes.map((f) => (
                <tr key={f.id}>
                  <td style={{ padding: 8, border: '1px solid #e5e7eb' }}>{f.fecha}</td>
                  <td style={{ padding: 8, border: '1px solid #e5e7eb' }}>{f.horaInicio}</td>
                  <td style={{ padding: 8, border: '1px solid #e5e7eb' }}>{f.horaFin ?? '-'}</td>
                  <td style={{ padding: 8, border: '1px solid #e5e7eb' }}>{f.tipo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

