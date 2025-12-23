import React, { useEffect, useState } from 'react'
import api from '../utils/axios'

export interface SectorTemplate {
  id: number
  name: string
  branding: {
    color_primario: string
    plantilla_inicio: string
    icon?: string
  }
  modules_count: number
  categories: string[]
  currency: string
}

interface SectorPlantillaSelectorProps {
  value: number | null
  onChange: (sectorId: number | null) => void
  disabled?: boolean
  onTemplateSelected?: (template: SectorTemplate | null) => void
}

export const SectorPlantillaSelector: React.FC<SectorPlantillaSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  onTemplateSelected,
}) => {
  const [templates, setTemplates] = useState<SectorTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setLoading(true)
        const response = await api.get('/v1/sectors/')
        setTemplates(response.data.templates || [])
        setError(null)
      } catch (err: any) {
        console.error('Error fetching sector templates:', err)
        setError(err.response?.data?.detail || 'Error cargando plantillas de sector')
      } finally {
        setLoading(false)
      }
    }

    fetchTemplates()
  }, [])

  const handleSelect = (id: number) => {
    if (disabled) return
    const nextValue = value === id ? null : id
    onChange(nextValue)
    if (onTemplateSelected) {
      const template = templates.find((tpl) => tpl.id === id) || null
      onTemplateSelected(nextValue ? template : null)
    }
  }

  const getIcon = (template: SectorTemplate) => {
    // FASE 7: Obtener icon de BD, no hardcodeado
    return template.branding?.icon || '🏢'
  }

  if (loading) {
    return (
      <div className="sector-selector-loading">
        <div className="spinner"></div>
        <p>Cargando plantillas de sector...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="sector-selector-error">
        <p style={{ color: '#dc2626' }}>⚠️ {error}</p>
        <button onClick={() => window.location.reload()}>Reintentar</button>
      </div>
    )
  }

  return (
    <div className="sector-plantilla-selector">
      <div className="sector-header">
        <h3>Tipo de Negocio *</h3>
        <p className="sector-description">
          Selecciona el sector para configurar branding y categorías por defecto. Los módulos se activarán manualmente después.
        </p>
      </div>

      <div className="templates-grid">
        {templates.map((template) => {
          const isSelected = value === template.id

          return (
            <div
              key={template.id}
              className={`template-card ${isSelected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
              onClick={() => handleSelect(template.id)}
              style={{
                borderColor: isSelected ? template.branding.color_primario : '#e5e7eb',
                backgroundColor: isSelected ? `${template.branding.color_primario}08` : '#fff',
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.6 : 1
              }}
            >
              <div
                className="template-icon"
                style={{
                  background: `linear-gradient(135deg, ${template.branding.color_primario}, ${template.branding.color_primario}dd)`,
                  color: '#fff'
                }}
              >
                <span style={{ fontSize: '2rem' }}>{getIcon(template)}</span>
              </div>

              <div className="template-content">
                <h4>{template.name}</h4>

                <div className="template-stats">
                  <span className="stat">
                    <strong>{template.categories.length}</strong> categorías por defecto
                  </span>
                </div>

                <div className="template-categories">
                  <small>{template.categories.slice(0, 3).join(', ')}</small>
                  {template.categories.length > 3 && (
                    <small className="more">+{template.categories.length - 3} más</small>
                  )}
                </div>

                <div
                  className="template-color-badge"
                  style={{ backgroundColor: template.branding.color_primario }}
                >
                  {template.branding.color_primario}
                </div>
              </div>

              {isSelected && (
                <div className="selected-indicator">✓</div>
              )}
            </div>
          )
        })}
      </div>



      <style>{`
        .sector-plantilla-selector {
          margin: 20px 0;
        }

        .sector-header {
          margin-bottom: 20px;
        }

        .sector-header h3 {
          margin: 0 0 8px 0;
          font-size: 18px;
          font-weight: 600;
          color: #111827;
        }

        .sector-description {
          margin: 0 0 12px 0;
          font-size: 14px;
          color: #6b7280;
        }

        .btn-link {
          background: none;
          border: none;
          color: #3b82f6;
          cursor: pointer;
          font-size: 13px;
          padding: 0;
          text-decoration: underline;
        }

        .templates-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .template-card {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 20px;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          transition: all 0.2s ease;
        }

        .template-card:not(.disabled):hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .template-card.selected {
          border-width: 3px;
        }

        .template-icon {
          width: 80px;
          height: 80px;
          border-radius: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 16px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .template-content {
          text-align: center;
          width: 100%;
        }

        .template-content h4 {
          margin: 0 0 12px 0;
          font-size: 16px;
          font-weight: 600;
          color: #111827;
        }

        .template-stats {
          display: flex;
          justify-content: center;
          gap: 16px;
          margin-bottom: 8px;
        }

        .stat {
          font-size: 13px;
          color: #6b7280;
        }

        .stat strong {
          color: #111827;
          font-weight: 600;
        }

        .template-categories {
          font-size: 12px;
          color: #9ca3af;
          margin-bottom: 12px;
          min-height: 32px;
        }

        .template-categories .more {
          font-weight: 600;
          color: #6b7280;
          margin-left: 4px;
        }

        .template-color-badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 999px;
          color: #fff;
          font-size: 11px;
          font-family: monospace;
          font-weight: 600;
        }

        .selected-indicator {
          position: absolute;
          top: 12px;
          right: 12px;
          width: 32px;
          height: 32px;
          background: #10b981;
          color: #fff;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          font-weight: bold;
        }

        .template-details {
          margin-top: 20px;
          padding: 20px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .details-panel h4 {
          margin: 0 0 12px 0;
          font-size: 15px;
          font-weight: 600;
          color: #111827;
        }

        .details-panel ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .details-panel li {
          padding: 8px 0;
          font-size: 14px;
          color: #374151;
          border-bottom: 1px solid #e5e7eb;
        }

        .details-panel li:last-child {
          border-bottom: none;
        }

        .color-preview {
          display: inline-block;
          padding: 2px 8px;
          margin-left: 8px;
          border-radius: 4px;
          color: #fff;
          font-size: 11px;
          font-family: monospace;
        }

        .categories-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 6px;
        }

        .category-tag {
          display: inline-block;
          padding: 4px 10px;
          background: #fff;
          border: 1px solid #d1d5db;
          border-radius: 999px;
          font-size: 12px;
          color: #374151;
        }

        .sector-selector-loading,
        .sector-selector-error {
          text-align: center;
          padding: 40px;
        }

        .spinner {
          width: 40px;
          height: 40px;
          margin: 0 auto 12px;
          border: 4px solid #f3f4f6;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default SectorPlantillaSelector
