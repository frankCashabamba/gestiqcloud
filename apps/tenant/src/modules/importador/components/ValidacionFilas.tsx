import React from 'react'

export default function ValidacionFilas({ errores }: { errores: string[] }) {
  return (
    <div>
      <h3 className="font-semibold mb-2">Validación</h3>
      {errores.length === 0 ? (
        <div className="text-green-700">Sin errores críticos.</div>
      ) : (
        <ul className="text-red-700 list-disc pl-5 text-sm">
          {errores.map((e, i) => <li key={i}>{e}</li>)}
        </ul>
      )}
    </div>
  )
}

