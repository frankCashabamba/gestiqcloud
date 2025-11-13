/**
 * ValidationErrorsByCountry - Agrupa errores por validador de país
 * Sprint 3: Errores organizados por país y tipo de validador
 */
import React, { useState, useMemo } from 'react'

interface ValidationError {
  rowNumber: number
  field: string
  message: string
  country?: string
  validator?: string
  severity: 'error' | 'warning'
}

interface ValidationErrorsByCountryProps {
  errors: ValidationError[]
  totalRows: number
}

interface CountryGroup {
  country: string
  validator: string
  errors: ValidationError[]
  severity: 'error' | 'warning'
}

const COUNTRY_FLAGS: Record<string, string> = {
  ec: '🇪🇨',
  es: '🇪🇸',
  pe: '🇵🇪',
  co: '🇨🇴',
  mx: '🇲🇽',
  ar: '🇦🇷',
  cl: '🇨🇱',
  other: '🌍'
}

const COUNTRY_NAMES: Record<string, string> = {
  ec: 'Ecuador',
  es: 'España',
  pe: 'Perú',
  co: 'Colombia',
  mx: 'México',
  ar: 'Argentina',
  cl: 'Chile',
  other: 'Otros'
}

export const ValidationErrorsByCountry: React.FC<ValidationErrorsByCountryProps> = ({
  errors,
  totalRows
}) => {
  const [expandedCountries, setExpandedCountries] = useState<Set<string>>(new Set())
  const [expandedValidators, setExpandedValidators] = useState<Set<string>>(new Set())

  const groupedErrors = useMemo(() => {
    const groups: Record<string, CountryGroup> = {}

    errors.forEach((error) => {
      const country = error.country || 'other'
      const validator = error.validator || 'generic'
      const key = `${country}-${validator}`

      if (!groups[key]) {
        groups[key] = {
          country,
          validator,
          errors: [],
          severity: error.severity
        }
      }

      groups[key].errors.push(error)
    })

    return Object.values(groups).sort((a, b) => {
      if (a.country !== b.country) return a.country.localeCompare(b.country)
      return a.validator.localeCompare(b.validator)
    })
  }, [errors])

  const countryGroups = useMemo(() => {
    const groups: Record<string, CountryGroup[]> = {}

    groupedErrors.forEach((group) => {
      if (!groups[group.country]) {
        groups[group.country] = []
      }
      groups[group.country].push(group)
    })

    return groups
  }, [groupedErrors])

  const toggleCountry = (country: string) => {
    const newSet = new Set(expandedCountries)
    if (newSet.has(country)) {
      newSet.delete(country)
    } else {
      newSet.add(country)
    }
    setExpandedCountries(newSet)
  }

  const toggleValidator = (key: string) => {
    const newSet = new Set(expandedValidators)
    if (newSet.has(key)) {
      newSet.delete(key)
    } else {
      newSet.add(key)
    }
    setExpandedValidators(newSet)
  }

  const errorRate = Math.round((errors.length / totalRows) * 100)

  if (errors.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-800">
          <span className="text-2xl">✅</span>
          <div>
            <strong>Sin errores</strong>
            <p className="text-sm text-green-700 mt-1">Todas las filas pasaron validación</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <div className="text-2xl font-bold text-red-700">{errors.filter(e => e.severity === 'error').length}</div>
          <div className="text-sm text-red-600">Errores críticos</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded p-3">
          <div className="text-2xl font-bold text-amber-700">{errors.filter(e => e.severity === 'warning').length}</div>
          <div className="text-sm text-amber-600">Advertencias</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded p-3">
          <div className="text-2xl font-bold text-blue-700">{errorRate}%</div>
          <div className="text-sm text-blue-600">Tasa de error</div>
        </div>
      </div>

      {/* By Country */}
      <div className="space-y-3">
        {Object.entries(countryGroups).map(([country, validators]) => (
          <div key={country} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Country Header */}
            <button
              onClick={() => toggleCountry(country)}
              className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{COUNTRY_FLAGS[country] || COUNTRY_FLAGS.other}</span>
                <div className="text-left">
                  <strong className="text-gray-800">{COUNTRY_NAMES[country] || country}</strong>
                  <p className="text-xs text-gray-600">
                    {validators.reduce((sum, v) => sum + v.errors.length, 0)} errores
                  </p>
                </div>
              </div>
              <div className="text-gray-600 text-lg">
                {expandedCountries.has(country) ? '▼' : '▶'}
              </div>
            </button>

            {/* Validators for Country */}
            {expandedCountries.has(country) && (
              <div className="border-t border-gray-200 bg-white">
                {validators.map((group) => {
                  const key = `${country}-${group.validator}`
                  return (
                    <div key={key} className="border-b border-gray-200 last:border-b-0">
                      {/* Validator Header */}
                      <button
                        onClick={() => toggleValidator(key)}
                        className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-50 transition"
                      >
                        <div className="flex items-center gap-3 flex-1">
                          <span className={`text-lg ${group.severity === 'error' ? '🚫' : '⚠️'}`} />
                          <div className="text-left">
                            <strong className="text-gray-700">{group.validator}</strong>
                            <p className="text-xs text-gray-500">{group.errors.length} errores</p>
                          </div>
                        </div>
                        <div className="text-gray-600">
                          {expandedValidators.has(key) ? '▼' : '▶'}
                        </div>
                      </button>

                      {/* Errors List */}
                      {expandedValidators.has(key) && (
                        <div className="bg-gray-50 px-6 py-3 space-y-2 max-h-96 overflow-y-auto">
                          {group.errors.slice(0, 10).map((error, idx) => (
                            <div
                              key={idx}
                              className={`text-sm p-2 rounded border-l-4 ${
                                error.severity === 'error'
                                  ? 'bg-red-50 border-red-400 text-red-700'
                                  : 'bg-amber-50 border-amber-400 text-amber-700'
                              }`}
                            >
                              <strong>Fila {error.rowNumber}:</strong> {error.field}
                              <div className="text-xs mt-1">{error.message}</div>
                            </div>
                          ))}
                          {group.errors.length > 10 && (
                            <div className="text-xs text-gray-600 text-center py-2">
                              +{group.errors.length - 10} más...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Recommendations */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-bold text-blue-900 mb-2">💡 Recomendaciones</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          {Object.keys(countryGroups).length > 1 && (
            <li>✓ Los errores provienen de {Object.keys(countryGroups).length} países diferentes</li>
          )}
          <li>✓ Revisa primero los errores críticos (🚫) antes de advertencias (⚠️)</li>
          <li>✓ Agrupa las filas por país para procesar validaciones específicas</li>
        </ul>
      </div>
    </div>
  )
}
