import React, { useState } from 'react'
import ImportadorLayout from '../components/ImportadorLayout'
import TemplateManager from '../components/TemplateManager'

export default function TemplatesPage() {
  const [open, setOpen] = useState(true)

  return (
    <ImportadorLayout
      title="Templates V2"
      description="Crea, edita y prueba plantillas de importación sin salir del importador."
    >
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-sm text-slate-600 mb-3">
          Usa este panel para gestionar plantillas V2. Selecciona un tipo de fuente y guarda.
        </p>
        <button
          onClick={() => setOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm"
        >
          Abrir gestor de templates
        </button>
      </div>
      <TemplateManager
        isOpen={open}
        onClose={() => setOpen(false)}
        onSelect={() => setOpen(false)}
        sourceType="products"
      />
    </ImportadorLayout>
  )
}
