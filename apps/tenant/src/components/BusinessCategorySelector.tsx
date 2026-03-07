/**
 * BusinessCategorySelector
 *
 * Displays a business category selector loaded dynamically from DB.
 * Replaces previously hardcoded values.
 *
 * Props:
 * - value: Selected category code
 * - onChange: Callback when a category is selected
 * - disabled: Disable selector
 * - label: Select label
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
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
  label,
  placeholder,
  className = '',
}: BusinessCategorySelectorProps) {
  const { t } = useTranslation()
  const { categories, loading, error } = useBusinessCategories()

  const resolvedLabel = label ?? t('components.categorySelector.label')
  const resolvedPlaceholder = placeholder ?? t('components.categorySelector.placeholder')

  return (
    <div className={`business-category-selector ${className}`}>
      {resolvedLabel && <label htmlFor="category-select">{resolvedLabel}</label>}

      <select
        id="category-select"
        value={value || ''}
        onChange={e => onChange?.(e.target.value)}
        disabled={disabled || loading}
        className={`select ${error ? 'error' : ''}`}
      >
        <option value="">{resolvedPlaceholder}</option>
        {categories.map(category => (
          <option key={category.code} value={category.code}>
            {category.name}
            {category.description && ` - ${category.description}`}
          </option>
        ))}
      </select>

      {loading && <small className="text-muted">{t('components.categorySelector.loading')}</small>}
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
          color: var(--gc-foreground);
        }

        .business-category-selector select {
          padding: 8px 12px;
          border: 1px solid var(--gc-border);
          border-radius: 4px;
          font-size: 14px;
          background-color: var(--gc-surface);
          cursor: pointer;
          transition: border-color 0.2s;
        }

        .business-category-selector select:hover:not(:disabled) {
          border-color: var(--gc-primary);
        }

        .business-category-selector select:focus:not(:disabled) {
          outline: none;
          border-color: var(--gc-primary);
          box-shadow: 0 0 0 3px color-mix(in srgb, var(--gc-primary) 10%, transparent);
        }

        .business-category-selector select:disabled {
          background-color: var(--gc-bg);
          cursor: not-allowed;
          opacity: 0.6;
        }

        .business-category-selector select.error {
          border-color: var(--gc-danger);
        }

        .business-category-selector small {
          font-size: 12px;
          margin-top: 4px;
        }

        .text-muted {
          color: var(--gc-muted);
        }

        .text-danger {
          color: var(--gc-danger);
        }
      `}</style>
    </div>
  )
}

export default BusinessCategorySelector
