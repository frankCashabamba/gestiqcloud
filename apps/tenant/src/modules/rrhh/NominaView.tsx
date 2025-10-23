import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useNomina } from './hooks/useNomina'

export default function NominaView() {
  const navigate = useNavigate()
  const { recibos, loading } = useNomina()

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        <button
          onClick={() => navigate(-1)}
          style={{ marginRight: 16, padding: '8px 12px', background: '#6b7280', color: 'white', border: 'none', borderRadius: 4 }}
        >
          ← Volver
        </button>
        <h2 style={{ fontWeight: 700, fontSize: 18 }}>Nómina</h2>
      </div>
      {loading ? (
        <div>Cargando…</div>
      ) : (
        <ul style={{ display: 'grid', gap: 8 }}>
          {recibos.map((r) => (
            <li key={r.id} style={{ padding: 12, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
              {r.empleado} — {r.mes} — $ {r.monto}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

