/**
 * SectorBadge
 *
 * Badge visual que muestra el sector/plantilla activa del tenant
 * Incluye icono dinámico y color según tipo de negocio
 *
 * FASE 5: Usa useSectorFullConfig() que carga desde BD
 * en lugar de datos hardcodeados (migrado desde useSectorConfig)
 */
import React from 'react'
import { useTenantSector, useTenantConfig } from '../contexts/TenantConfigContext'
import { useSectorFullConfig, getSectorIcon, getSectorColor, getSectorDisplayName } from '../hooks/useSectorFullConfig'

interface SectorBadgeProps {
  /** Tamaño del badge */
  size?: 'sm' | 'md' | 'lg'
  /** Mostrar nombre completo o solo icono */
  showLabel?: boolean
  /** Clase CSS adicional */
  className?: string
}

export function SectorBadge({
  size = 'md',
  showLabel = true,
  className = ''
}: SectorBadgeProps) {
  const sector = useTenantSector()
  const { config } = useTenantConfig()

  // FASE 5: Cargar configuración completa del sector desde BD
  const { config: sectorConfig, loading, error } = useSectorFullConfig(sector?.plantilla)

  if (!sector || !sector.plantilla) {
    return null
  }

  // Si hay error cargando config, usar fallback
  if (error) {
    console.warn('Error loading sector config from DB:', error)
  }

  const icon = getSectorIcon(sectorConfig)
  const color = getSectorColor(sectorConfig)

  // Usar displayName de la BD si disponible, sino fallback a normalización manual
  const displayName = sectorConfig?.branding
    ? getSectorDisplayName(sectorConfig)
    : (config?.tenant?.plantilla_inicio || sector.plantilla)
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')

  return (
    <div
      className={`sector-badge sector-badge--${size} ${className}`}
      style={{
        backgroundColor: `${color}15`,
        borderColor: color,
        color: color
      }}
      role="status"
      aria-label={`Sector active: ${displayName}`}
    >
      <span className="badge-icon" aria-hidden="true">
        {icon}
      </span>
      {showLabel && (
        <span className="badge-label">
          {displayName}
        </span>
      )}

      <style>{`
        .sector-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          border: 1.5px solid;
          border-radius: 8px;
          font-weight: 600;
          white-space: nowrap;
          transition: all 0.2s ease;
        }

        .sector-badge:hover {
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        /* Tamaños */
        .sector-badge--sm {
          padding: 4px 8px;
          font-size: 11px;
          gap: 4px;
        }

        .sector-badge--sm .badge-icon {
          font-size: 14px;
        }

        .sector-badge--md {
          padding: 6px 12px;
          font-size: 13px;
          gap: 6px;
        }

        .sector-badge--md .badge-icon {
          font-size: 16px;
        }

        .sector-badge--lg {
          padding: 8px 16px;
          font-size: 14px;
          gap: 8px;
        }

        .sector-badge--lg .badge-icon {
          font-size: 20px;
        }

        .badge-icon {
          display: flex;
          align-items: center;
          line-height: 1;
        }

        .badge-label {
          letter-spacing: 0.2px;
        }

        /* Responsive */
        @media (max-width: 640px) {
          .sector-badge--md {
            padding: 5px 10px;
            font-size: 12px;
          }

          .sector-badge--lg {
            padding: 7px 14px;
            font-size: 13px;
          }
        }
      `}</style>
    </div>
  )
}

export default SectorBadge
