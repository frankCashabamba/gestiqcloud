import React from 'react'

export default function ResumenImportacion({ total, onBack, onImport }: { total: number; onBack: ()=>void; onImport: ()=>void }) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Resumen</h3>
      <div className="text-sm text-gray-700">Filas a importar: {total}</div>
      <div className="mt-2 flex gap-2">
        <button className="bg-gray-200 px-3 py-1 rounded" onClick={onBack}>Volver</button>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={onImport}>Importar</button>
      </div>
    </div>
  )
}

