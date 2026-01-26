import React from 'react'

export default function EinvoicingPlaceholder() {
  return (
    <div className="p-6">
      <div className="max-w-2xl mx-auto text-center">
        <div className="text-6xl mb-4">📄</div>
        <h1 className="text-2xl font-bold text-gray-800 mb-2">
          Facturación Electrónica
        </h1>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <span className="text-yellow-800 font-medium">🚧 Módulo en desarrollo</span>
        </div>
        <p className="text-gray-600 mb-4">
          Este módulo permitirá gestionar la emisión, validación y envío de
          facturas electrónicas según las normativas fiscales de cada país.
        </p>
        <div className="bg-gray-50 rounded-lg p-4 text-left">
          <h3 className="font-semibold text-gray-700 mb-2">Funcionalidades planificadas:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Emisión de facturas electrónicas</li>
            <li>• Validación con autoridades fiscales</li>
            <li>• Formatos por país (XML, JSON, UBL)</li>
            <li>• Notas de crédito y débito electrónicas</li>
            <li>• Historial de transmisiones</li>
          </ul>
        </div>
        <div className="mt-6 text-xs text-gray-400">
          Backend: apps/backend/app/modules/einvoicing
        </div>
      </div>
    </div>
  )
}
