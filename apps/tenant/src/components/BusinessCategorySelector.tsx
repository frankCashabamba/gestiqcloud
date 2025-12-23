/**
 * BusinessCategorySelector
 *
 * Componente que muestra un selector de categorías de negocio
 * cargadas dinámicamente desde BD.
 *
 * Reemplaza valores hardcodeados previos.
 *
 * Props:
 * - value: Código de categoría seleccionada
 * - onChange: Callback cuando selecciona una categoría
 * - disabled: Desabilitar selector
 * - label: Label del select
 */

import React from 'react'
import { useBusinessCategories } from '../hooks/useBusinessCategories'

interface BusinessCategorySelectorProps {
  value?: string | null
  onChange?: (categoryCode: string) => void
  disabled?: boolean
  label?: string
  placeholder?: string
  className?: string
}

export function BusinessCategorySelector({
  value,
  onChange,
  disabled = false,
  label = 'Categoría de Negocio',
  placeholder = 'Seleccionar categoría...',
  className = '',
}: BusinessCategorySelectorProps) {
  const { categories, loading, error } = useBusinessCategories()

  return (
    <div className={`business-category-selector ${className}`}>
      {label && <label htmlFor="category-select">{label}</label>}

      <select
        id="category-select"
        value={value || ''}
        onChange={e => onChange?.(e.target.value)}
        disabled={disabled || loading}
        className={`select ${error ? 'error' : ''}`}
      >
        <option value="">{placeholder}</option>
        {categories.map(category => (
          <option key={category.code} value={category.code}>
            {category.name}
            {category.description && ` - ${category.description}`}
          </option>
        ))}
      </select>

      {loading && <small className="text-muted">Cargando categorías...</small>}
      {error && <small className="text-danger">Error: {error}</small>}

      <style>{`
        .business-category-selector {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .business-category-selector label {
          font-weight: 600;
          font-size: 14px;
          color: #333;
        }

        .business-category-selector select {
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
          background-color: white;
          cursor: pointer;
          transition: border-color 0.2s;
        }

        .business-category-selector select:hover:not(:disabled) {
          border-color: #4f46e5;
        }

        .business-category-selector select:focus:not(:disabled) {
          outline: none;
          border-color: #4f46e5;
          box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }

        .business-category-selector select:disabled {
          background-color: #f5f5f5;
          cursor: not-allowed;
          opacity: 0.6;
        }

        .business-category-selector select.error {
          border-color: #dc2626;
        }

        .business-category-selector small {
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

export default BusinessCategorySelector
