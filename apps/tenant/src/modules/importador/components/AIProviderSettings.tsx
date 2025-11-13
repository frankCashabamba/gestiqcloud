/**
 * AIProviderSettings - UI para configurar proveedor IA
 * Sprint 2: Selector de proveedor (local, OpenAI, Azure)
 */
import React, { useState, useEffect } from 'react'

type AIProvider = 'local' | 'openai' | 'azure'

interface AIProviderSettingsProps {
  onSave?: (provider: AIProvider) => void
  initialProvider?: AIProvider
}

export const AIProviderSettings: React.FC<AIProviderSettingsProps> = ({
  onSave,
  initialProvider = 'local'
}) => {
  const [provider, setProvider] = useState<AIProvider>(initialProvider)
  const [isOpen, setIsOpen] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // Cargar proveedor guardado del localStorage
    const saved = localStorage.getItem('importador_ai_provider') as AIProvider | null
    if (saved) setProvider(saved)
  }, [])

  const handleSave = () => {
    localStorage.setItem('importador_ai_provider', provider)
    setSaved(true)
    onSave?.(provider)
    setTimeout(() => setSaved(false), 2000)
  }

  const providerInfo: Record<AIProvider, { icon: string; label: string; description: string; color: string }> = {
    local: {
      icon: '⚙️',
      label: 'Local (Gratuita)',
      description: 'Clasificación basada en heurísticas y patrones. Sin costos, pero menos precisión.',
      color: 'bg-blue-50 border-blue-200'
    },
    openai: {
      icon: '🤖',
      label: 'OpenAI GPT',
      description: 'GPT-3.5-turbo o GPT-4. Precisión muy alta, requiere API key.',
      color: 'bg-green-50 border-green-200'
    },
    azure: {
      icon: '☁️',
      label: 'Azure OpenAI',
      description: 'Azure OpenAI Service. Integración empresarial con Azure.',
      color: 'bg-purple-50 border-purple-200'
    }
  }

  const info = providerInfo[provider]

  return (
    <div className="relative">
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded border border-gray-300 hover:border-gray-400 bg-white hover:bg-gray-50 transition text-sm"
      >
        <span className="text-lg">{info.icon}</span>
        <span className="font-medium text-gray-700">{info.label}</span>
        <span className={`ml-1 text-gray-400 transition ${isOpen ? 'rotate-180' : ''}`}>⌄</span>
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute top-full mt-2 right-0 w-96 bg-white border border-gray-300 rounded-lg shadow-lg z-50 p-4 space-y-4">
          <div className="border-b pb-2">
            <h3 className="font-bold text-gray-800">Configuración de IA para Clasificación</h3>
            <p className="text-xs text-gray-600 mt-1">Selecciona el proveedor de clasificación automática</p>
          </div>

          {/* Provider Options */}
          <div className="space-y-3">
            {Object.entries(providerInfo).map(([key, data]) => (
              <label
                key={key}
                className={`flex items-start gap-3 p-3 rounded border-2 cursor-pointer transition ${
                  provider === key
                    ? `${data.color} border-current`
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="ai-provider"
                  value={key}
                  checked={provider === key}
                  onChange={(e) => setProvider(e.target.value as AIProvider)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="font-semibold text-gray-800 flex items-center gap-2">
                    <span className="text-xl">{data.icon}</span>
                    {data.label}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">{data.description}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Current Provider Info */}
          <div className={`border-2 rounded p-3 ${info.color}`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{info.icon}</span>
              <strong className="text-sm">{info.label}</strong>
            </div>
            <p className="text-xs text-gray-700 leading-relaxed">{info.description}</p>

            {/* Additional Notes */}
            {provider === 'local' && (
              <div className="mt-2 text-xs bg-white rounded p-2 border border-blue-200">
                <strong>Nota:</strong> Óptimo para empezar. Los resultados mejoran con datos de entrenamiento.
              </div>
            )}
            {provider === 'openai' && (
              <div className="mt-2 text-xs bg-white rounded p-2 border border-green-200">
                <strong>Configuración:</strong> Requiere OPENAI_API_KEY en el backend.
              </div>
            )}
            {provider === 'azure' && (
              <div className="mt-2 text-xs bg-white rounded p-2 border border-purple-200">
                <strong>Configuración:</strong> Requiere AZURE_OPENAI_KEY y AZURE_OPENAI_ENDPOINT.
              </div>
            )}
          </div>

          {/* Save Button */}
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium transition"
            >
              {saved ? '✓ Guardado' : 'Guardar Configuración'}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="px-3 py-2 rounded border border-gray-300 hover:bg-gray-50 text-sm font-medium transition"
            >
              Cerrar
            </button>
          </div>

          {/* Disclaimer */}
          <div className="text-xs text-gray-600 border-t pt-3">
            <p>💡 La configuración se guarda localmente en tu navegador. El backend respeta el proveedor configurado en variables de entorno.</p>
          </div>
        </div>
      )}
    </div>
  )
}
