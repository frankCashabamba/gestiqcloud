import React from 'react'
import { useFichajes } from './hooks/useFichajes'

export default function FichajesView() {
  const { fichajes, loading } = useFichajes()

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Timekeeping</h2>
      {loading ? (
        <div>Loading...</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
            <thead style={{ background: '#f3f4f6' }}>
              <tr>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Date</th>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Clock In</th>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Clock Out</th>
                <th style={{ padding: 8, border: '1px solid #e5e7eb' }}>Type</th>
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
