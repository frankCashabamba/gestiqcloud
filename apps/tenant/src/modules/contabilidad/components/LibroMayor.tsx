import React from 'react'
import { useMovimientos } from '../hooks/useMovimientos'
import { agruparPorCuenta } from '../utils/reportesContables'

export function LibroMayor() {
  const { asientos, loading } = useMovimientos()
  if (loading) return <div className="p-4 text-sm text-gray-500">Cargando…</div>
  const cuentas = agruparPorCuenta(asientos)

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-4">Libro Mayor</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>Cuenta</th>
            <th>Debe</th>
            <th>Haber</th>
            <th>Saldo</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(cuentas).map(([cuenta, v]) => {
            const saldo = (v.debe || 0) - (v.haber || 0)
            return (
              <tr key={cuenta} className="border-b">
                <td>{cuenta}</td>
                <td>{v.debe.toFixed(2)}</td>
                <td>{v.haber.toFixed(2)}</td>
                <td>{saldo.toFixed(2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

