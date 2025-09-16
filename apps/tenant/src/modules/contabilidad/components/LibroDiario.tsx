import React from 'react'
import { useMovimientos } from '../hooks/useMovimientos'

export function LibroDiario() {
  const { asientos, loading } = useMovimientos()
  if (loading) return <div className="p-4 text-sm text-gray-500">Cargando…</div>

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-4">Libro Diario</h2>
      {asientos.map((a) => (
        <div key={a.id} className="mb-4">
          <h3 className="font-medium">{a.fecha} - {a.concepto}</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th>Cuenta</th>
                <th>Descripción</th>
                <th>Debe</th>
                <th>Haber</th>
              </tr>
            </thead>
            <tbody>
              {a.apuntes.map((ap, i) => (
                <tr key={i} className="border-b">
                  <td>{ap.cuenta}</td>
                  <td>{ap.descripcion}</td>
                  <td>{ap.debe.toFixed(2)}</td>
                  <td>{ap.haber.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

