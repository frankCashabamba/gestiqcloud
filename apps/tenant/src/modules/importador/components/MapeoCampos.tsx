import React from 'react'

type Props = {
  headers: string[]
  camposObjetivo: string[]
  mapa: Partial<Record<string, string>>
  onChange: (m: Partial<Record<string,string>>) => void
}

export default function MapeoCampos({ headers, camposObjetivo, mapa, onChange }: Props) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Mapeo de campos</h3>
      <div className="grid md:grid-cols-2 gap-3">
        {camposObjetivo.map((campo) => (
          <div key={campo}>
            <label className="block text-sm mb-1">{campo}</label>
            <select
              className="border px-2 py-1 rounded text-sm w-full"
              value={mapa[campo] || ''}
              onChange={(e)=> onChange({ ...mapa, [campo]: e.target.value })}
            >
              <option value="">-- seleccionar columna --</option>
              {headers.map((h) => (
                <option key={h} value={h}>{h}</option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  )
}

