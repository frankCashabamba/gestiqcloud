/**
 * Hook para validaciones país-específicas
 * Se usa en formularios para dar feedback inmediato al usuario
 * Siempre validar también en backend como fuente de verdad
 */

import { useMemo } from 'react'
import CountryValidator, { type ValidationError } from '../modules/importer/utils/countryValidators'

export interface CountryValidationResult {
  isValid: boolean
  errors: ValidationError[]
  message?: string
}

/**
 * Hook para validar IDs fiscales según país
 * @param country ISO 3166-1 alpha-2 code (EC, AR, ES, etc.)
 * @param value Valor a validar
 * @returns Estado de validación
 *
 * @example
 * const { isValid, errors } = useCountryValidation('EC', rucValue)
 * if (!isValid) {
 *   errors.forEach(err => console.log(err.message))
 * }
 */
export function useCountryValidation(
  country: string | undefined,
  value: string | undefined
): CountryValidationResult {
  return useMemo(() => {
    if (!country || !value) {
      return { isValid: true, errors: [] }
    }

    const errors = CountryValidator.validateTaxID(country, value)

    return {
      isValid: errors.length === 0,
      errors,
      message: errors.length > 0 ? errors[0].message : undefined,
    }
  }, [country, value])
}

/**
 * Hook para validar números de documento según país
 */
export function useDocumentNumberValidation(
  country: string | undefined,
  documentType: string | undefined,
  value: string | undefined
): CountryValidationResult {
  return useMemo(() => {
    if (!country || !value) {
      return { isValid: true, errors: [] }
    }

    let errors: ValidationError[] = []

    const upperCountry = country.toUpperCase()

    // Ecuador-specific: validate Clave de Acceso
    if (upperCountry === 'EC' && documentType?.toUpperCase() === 'INVOICE') {
      errors = CountryValidator.validateAccessKey(country, value)
    }

    return {
      isValid: errors.length === 0,
      errors,
      message: errors.length > 0 ? errors[0].message : undefined,
    }
  }, [country, documentType, value])
}

/**
 * Hook genérico que retorna validador para el país actual
 * Útil para componentes reutilizables
 */
export function useCountryValidator(country: string | undefined) {
  return useMemo(() => {
    if (!country) {
      return null
    }

    return {
      validateTaxID: (value: string) => CountryValidator.validateTaxID(country, value),
      validateAccessKey: (value: string) => CountryValidator.validateAccessKey(country, value),
      validateRUC: (value: string) => CountryValidator.validateEcuadorRUC(value),
      validateCUIT: (value: string) => CountryValidator.validateArgentinaCUIT(value),
      validateNIF: (value: string) => CountryValidator.validateSpainNIF(value),
    }
  }, [country])
}

export default useCountryValidation
