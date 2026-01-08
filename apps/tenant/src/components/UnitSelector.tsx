/**
 * UnitSelector Component
 *
 * Componente que muestra selector de unidades de medida
 * cargadas dinámicamente desde BD.
 *
 * Reemplaza hardcoding de getSectorUnits() en sectorHelpers.ts
 *
 * Props:
 * - value: Código de unidad seleccionada
 * - onChange: Callback cuando selecciona una unidad
 * - disabled: Deshabilitar selector
 * - label: Label del select
 * - sectorCode: Código del sector (opcional, usa company config si no se pasa)
 */

import React from 'react'
import { useUnitsBySector } from '../hooks/useUnits'

interface UnitSelectorProps {
  value?: string | null
  onChange?: (unitCode: string) => void
  disabled?: boolean
  label?: string
  placeholder?: string
  className?: string
  sectorCode?: string | null
}

export function UnitSelector({
  value,
  onChange,
  disabled = false,
  label = 'Unidad de Medida',
  placeholder = 'Seleccionar unidad...',
  className = '',
  sectorCode,
}: UnitSelectorProps) {
  const { units, loading, error } = useUnitsBySector(sectorCode)

  return (
    <div className={`unit-selector ${className}`}>
      {label && <label htmlFor="unit-select">{label}</label>}

      <select
        id="unit-select"
        value={value || ''}
        onChange={e => onChange?.(e.target.value)}
        disabled={disabled || loading}
        className={`select ${error ? 'error' : ''}`}
      >
        <option value="">{placeholder}</option>
        {units.map(unit => (
          <option key={unit.code} value={unit.code}>
            {unit.label}
          </option>
        ))}
      </select>

      {loading && <small className="text-muted">Cargando unidades...</small>}
      {error && <small className="text-danger">Error: {error}</small>}

      <style>{`
        .unit-selector {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .unit-selector label {
          font-weight: 600;
          font-size: 14px;
          color: #333;
        }

        .unit-selector select {
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
          background-color: white;
          cursor: pointer;
          transition: border-color 0.2s;
        }

        .unit-selector select:hover:not(:disabled) {
          border-color: #4f46e5;
        }

        .unit-selector select:focus:not(:disabled) {
          outline: none;
          border-color: #4f46e5;
          box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }

        .unit-selector select:disabled {
          background-color: #f5f5f5;
          cursor: not-allowed;
          opacity: 0.6;
        }

        .unit-selector select.error {
          border-color: #dc2626;
        }

        .unit-selector small {
          font-size: 12px;
          margin-top: 4px;
        }

        .text-muted {
          color: #666;
        }

        .text-danger {
          color: #dc2626;
        }
      `}</style>
    </div>
  )
}

export default UnitSelector
