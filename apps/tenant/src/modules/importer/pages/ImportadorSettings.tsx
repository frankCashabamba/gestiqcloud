/**
 * ImportadorSettings - Página de configuración para el módulo importador
 * Sprint 2: Configuración de IA, parsers y comportamiento
 */
import React, { useState } from 'react'
import { AIProviderSettings } from '../components/AIProviderSettings'

export default function ImportadorSettings() {
  const [activeTab, setActiveTab] = useState<'ia' | 'importacion'>('ia')

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Configuración del Importador</h1>
      <p className="text-gray-600 mb-6">Personaliza el comportamiento del módulo de importaciones</p>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('ia')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'ia'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-800'
          }`}
        >
          🤖 Configuración IA
        </button>
        <button
          onClick={() => setActiveTab('importacion')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'importacion'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-800'
          }`}
        >
          ⚙️ Importación
        </button>
      </div>

      {/* IA Tab */}
      {activeTab === 'ia' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>🤖</span> Proveedor de Clasificación IA
            </h2>

            <p className="text-gray-700 mb-4">
              El importador puede usar diferentes proveedores de IA para clasificar archivos automáticamente.
              Selecciona el que mejor se adapte a tus necesidades:
            </p>

            <div className="mb-6">
              <AIProviderSettings />
            </div>

            <div className="bg-white border border-blue-200 rounded p-4 text-sm space-y-3">
              <div>
                <strong className="text-blue-700">📊 Local (Gratuita)</strong>
                <p className="text-gray-600 text-xs mt-1">
                  Usa heurísticas y análisis de patrones. Sin costos. Perfecto para empezar.
                </p>
              </div>
              <div>
                <strong className="text-green-700">🤖 OpenAI GPT</strong>
                <p className="text-gray-600 text-xs mt-1">
                  Usa GPT-3.5-turbo o GPT-4 (configurable). Muy preciso pero tiene costos por uso.
                  Requiere OPENAI_API_KEY.
                </p>
              </div>
              <div>
                <strong className="text-purple-700">☁️ Azure OpenAI</strong>
                <p className="text-gray-600 text-xs mt-1">
                  Integración con Azure OpenAI Service. Ideal para empresas con infraestructura Azure.
                  Requiere AZURE_OPENAI_KEY y AZURE_OPENAI_ENDPOINT.
                </p>
              </div>
            </div>
          </div>

          {/* Caché */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-bold mb-3">⚡ Optimizaciones</h3>
            <label className="flex items-start gap-3 p-3 border border-gray-300 rounded hover:bg-gray-100 cursor-pointer">
              <input type="checkbox" defaultChecked className="mt-1" />
              <div>
                <strong>Caché de clasificaciones</strong>
                <p className="text-xs text-gray-600 mt-1">
                  Almacena resultados de clasificación por 24h para evitar llamadas repetidas a IA
                </p>
              </div>
            </label>
          </div>
        </div>
      )}

      {/* Importación Tab */}
      {activeTab === 'importacion' && (
        <div className="space-y-6">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>⚙️</span> Comportamiento de Importación
            </h2>

            <div className="space-y-4">
              {/* Auto-mapping */}
              <label className="flex items-start gap-3 p-3 border border-gray-300 rounded hover:bg-white cursor-pointer">
                <input type="checkbox" defaultChecked className="mt-1" />
                <div>
                  <strong>Mapeo automático de columnas</strong>
                  <p className="text-xs text-gray-600 mt-1">
                    Suiere automáticamente qué columnas mapear según Levenshtein distance
                  </p>
                </div>
              </label>

              {/* Preview */}
              <label className="flex items-start gap-3 p-3 border border-gray-300 rounded hover:bg-white cursor-pointer">
                <input type="checkbox" defaultChecked className="mt-1" />
                <div>
                  <strong>Mostrar vista previa</strong>
                  <p className="text-xs text-gray-600 mt-1">
                    Visualiza las primeras 50 filas antes de importar
                  </p>
                </div>
              </label>

              {/* Validación */}
              <label className="flex items-start gap-3 p-3 border border-gray-300 rounded hover:bg-white cursor-pointer">
                <input type="checkbox" defaultChecked className="mt-1" />
                <div>
                  <strong>Validación por país</strong>
                  <p className="text-xs text-gray-600 mt-1">
                    Aplica validadores específicos según país (RUC Ecuador, etc.)
                  </p>
                </div>
              </label>

              {/* Auto mode */}
              <label className="flex items-start gap-3 p-3 border border-gray-300 rounded hover:bg-white cursor-pointer">
                <input type="checkbox" defaultChecked className="mt-1" />
                <div>
                  <strong>Modo automático por defecto</strong>
                  <p className="text-xs text-gray-600 mt-1">
                    Activa productos, crea almacén si falta y aplica stock inicial automáticamente
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Límites */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-bold mb-3">📋 Límites</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border border-blue-200 rounded p-3">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Máximo de filas por importación
                </label>
                <input type="number" defaultValue="10000" className="w-full border border-gray-300 rounded px-2 py-1" />
              </div>
              <div className="bg-white border border-blue-200 rounded p-3">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Maximum errors before cancel
                </label>
                <input type="number" defaultValue="100" className="w-full border border-gray-300 rounded px-2 py-1" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 flex gap-2">
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium">
          Save changes
        </button>
        <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded font-medium">
          Cancel
        </button>
      </div>
    </div>
  )
}
