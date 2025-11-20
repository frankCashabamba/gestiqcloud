import React from 'react'

export default function ImportarEmpresas() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200">
        <header className="px-6 py-5 border-b border-slate-200">
          <h1 className="text-2xl font-semibold text-slate-900">Importar empresas (Excel)</h1>
          <p className="text-slate-500 text-sm mt-1">
            Carga un archivo .xlsx con el formato indicado para crear empresas en lote.
          </p>
        </header>
        <div className="px-6 py-8">
          <div className="rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <p className="text-sm text-slate-600 mb-3">Arrastra aquí tu archivo .xlsx o haz clic para seleccionarlo</p>
            <input type="file" accept=".xlsx,.xls" className="mx-auto block" disabled title="Próximamente" />
            <p className="text-xs text-slate-500 mt-4">Próximamente habilitaremos la validación y vista previa antes de importar.</p>
          </div>
          <section className="mt-8">
            <h2 className="text-sm font-semibold text-slate-700 mb-2">Formato esperado</h2>
            <ul className="text-sm text-slate-600 list-disc pl-5 space-y-1">
              <li>Columnas: nombre_empresa, ruc, telefono, direccion, pais, provincia, ciudad, cp, sitio_web, nombre_encargado, apellido_encargado, email, modulos</li>
              <li>Separar múltiples módulos por coma (por ejemplo: importador,ventas,facturacion)</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
