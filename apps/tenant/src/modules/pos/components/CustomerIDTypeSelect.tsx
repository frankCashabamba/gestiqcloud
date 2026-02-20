/**
 * Customer ID Type Select Component
 *
 * Replaces hardcoded DEFAULT_ID_TYPES with dynamic values from API
 * Usage:
 *   <CustomerIDTypeSelect
 *     value={selectedIdType}
 *     onChange={handleIdTypeChange}
 *   />
 */

import React from 'react'
import { useDocumentIDTypes } from '../../../hooks/useDocumentIDTypes'
import { useTranslation } from 'react-i18next'

interface CustomerIDTypeSelectProps {
  value?: string
  onChange: (code: string) => void
  disabled?: boolean
  countryCode?: string
  className?: string
}

export function CustomerIDTypeSelect({
  value,
  onChange,
  disabled = false,
  countryCode,
  className = '',
}: CustomerIDTypeSelectProps) {
  const { data: idTypes, loading, error } = useDocumentIDTypes({ country_code: countryCode })
  const { t } = useTranslation('pos')

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="id-type" className="text-sm font-medium text-gray-700">
        {t('pos:customer.idType')}
      </label>

      <select
        id="id-type"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || loading}
        className={`
          px-3 py-2 border border-gray-300 rounded-md
          focus:outline-none focus:ring-2 focus:ring-blue-500
          disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed
          ${className}
        `}
      >
        <option value="">
          {loading ? t('common:loading') : t('pos:selectIDType')}
        </option>

        {idTypes.map((idType) => (
          <option key={idType.code} value={idType.code}>
            {idType.name_es || idType.name_en} ({idType.code})
          </option>
        ))}
      </select>

      {error && (
        <p className="text-xs text-red-600">
          {t('common:error')}: {error.message}
        </p>
      )}

      {/* Show validation pattern if available */}
      {value && idTypes.length > 0 && (
        (() => {
          const selected = idTypes.find((t) => t.code === value)
          return selected?.regex_pattern ? (
            <p className="text-xs text-gray-500">
              Format: {selected.regex_pattern}
            </p>
          ) : null
        })()
      )}
    </div>
  )
}

export default CustomerIDTypeSelect
