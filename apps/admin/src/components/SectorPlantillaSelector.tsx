import React, { useEffect, useState } from 'react'

import api from '../utils/axios'

export interface SectorTemplate {
  id: number
  name: string
  branding: {
    primaryColor: string
    secondaryColor?: string
    startTemplate: string
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

  const getIcon = (template: SectorTemplate) => template.branding?.icon || '🏢'

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
        <h3>Tipo de negocio *</h3>
        <p className="sector-description">Elige una base y sigue. El resto se puede ajustar después.</p>
      </div>

      <div className="templates-grid">
        {templates.map((template) => {
          const isSelected = value === template.id

          return (
            <button
              key={template.id}
              type="button"
              className={`template-card ${isSelected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
              onClick={() => handleSelect(template.id)}
              style={{
                borderColor: isSelected ? template.branding.primaryColor : '#e5e7eb',
                backgroundColor: isSelected ? `${template.branding.primaryColor}08` : '#fff',
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.6 : 1,
              }}
            >
              <div
                className="template-icon"
                style={{
                  background: `linear-gradient(135deg, ${template.branding.primaryColor}, ${template.branding.primaryColor}dd)`,
                  color: '#fff',
                }}
              >
                <span>{getIcon(template)}</span>
              </div>

              <div className="template-content">
                <div className="template-head">
                  <h4>{template.name}</h4>
                  {isSelected && <div className="selected-indicator">✓</div>}
                </div>
                <div className="template-stats">
                  <span className="stat">
                    <strong>{template.categories.length}</strong> categorías
                  </span>
                  {template.currency && <span className="stat">{template.currency}</span>}
                </div>
                <div className="template-categories" title={template.categories.join(', ')}>
                  <small>{template.categories.slice(0, 3).join(', ')}</small>
                  {template.categories.length > 3 && <small className="more">+{template.categories.length - 3}</small>}
                </div>
                <div className="template-color-badges">
                  <div className="template-color-badge" style={{ backgroundColor: template.branding.primaryColor }}>
                    {template.branding.primaryColor}
                  </div>
                  {template.branding.secondaryColor && (
                    <div className="template-color-badge dark" style={{ backgroundColor: template.branding.secondaryColor }}>
                      {template.branding.secondaryColor}
                    </div>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      <style>{`
        .sector-plantilla-selector {
          margin: 6px 0 0;
        }

        .sector-header {
          margin-bottom: 10px;
        }

        .sector-header h3 {
          margin: 0 0 4px 0;
          font-size: 15px;
          font-weight: 600;
          color: #111827;
        }

        .sector-description {
          margin: 0;
          font-size: 12px;
          color: #6b7280;
        }

        .templates-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
          gap: 10px;
        }

        .template-card {
          position: relative;
          display: grid;
          grid-template-columns: 44px minmax(0, 1fr);
          gap: 10px;
          align-items: start;
          width: 100%;
          padding: 12px;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          transition: all 0.18s ease;
          text-align: left;
        }

        .template-card:not(.disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 3px 10px rgba(15, 23, 42, 0.08);
        }

        .template-card.selected {
          border-width: 2px;
          box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
        }

        .template-icon {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
          font-size: 20px;
        }

        .template-content {
          min-width: 0;
        }

        .template-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 8px;
        }

        .template-content h4 {
          margin: 0 0 4px 0;
          font-size: 14px;
          font-weight: 600;
          line-height: 1.25;
          color: #111827;
        }

        .template-stats {
          display: flex;
          flex-wrap: wrap;
          gap: 6px 10px;
          margin-bottom: 4px;
        }

        .stat {
          font-size: 11px;
          color: #6b7280;
        }

        .stat strong {
          color: #111827;
          font-weight: 700;
        }

        .template-categories {
          font-size: 11px;
          color: #9ca3af;
          margin-bottom: 8px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .template-categories .more {
          margin-left: 4px;
          color: #6b7280;
          font-weight: 700;
        }

        .template-color-badges {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }

        .template-color-badge {
          display: inline-block;
          padding: 3px 8px;
          border-radius: 999px;
          color: #fff;
          font-size: 10px;
          font-family: monospace;
          font-weight: 700;
        }

        .selected-indicator {
          width: 18px;
          height: 18px;
          background: #10b981;
          color: #fff;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          font-weight: 700;
          flex-shrink: 0;
        }

        .sector-selector-loading,
        .sector-selector-error {
          text-align: center;
          padding: 28px;
        }

        .spinner {
          width: 30px;
          height: 30px;
          margin: 0 auto 10px;
          border: 3px solid #f3f4f6;
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
