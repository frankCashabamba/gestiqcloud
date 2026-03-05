/**
 * Country-specific validators for tax IDs and invoice numbers
 * Mirrors backend country_validators.py for consistent frontend UX
 * Source of truth: apps/backend/app/modules/imports/validators/country_validators.py
 */

export interface ValidationError {
  code: string
  message: string
}

export class CountryValidator {
  /**
   * Validates Ecuador RUC (Registro Único de Contribuyentes)
   *
   * Format: 13 digits
   * - Positions 1-2: Province code (01-24)
   * - Positions 3-8: Unique identification
   * - Position 9: Type (0=natural, 1=juridical, 6=government, 9=temporary)
   * - Positions 10-13: Sequential code
   */
  static validateEcuadorRUC(ruc: string): ValidationError[] {
    const errors: ValidationError[] = []

    if (!ruc) {
      return [{ code: 'EMPTY_VALUE', message: 'RUC cannot be empty' }]
    }

    if (!/^\d+$/.test(ruc)) {
      errors.push({
        code: 'INVALID_TAX_ID_FORMAT',
        message: 'RUC must contain only digits',
      })
      return errors
    }

    if (ruc.length !== 13) {
      errors.push({
        code: 'INVALID_TAX_ID_FORMAT',
        message: `RUC must be 13 digits, got ${ruc.length}`,
      })
      return errors
    }

    // Validate province code (01-24)
    const provinceCode = parseInt(ruc.substring(0, 2), 10)
    if (provinceCode < 1 || provinceCode > 24) {
      errors.push({
        code: 'INVALID_TAX_ID_FORMAT',
        message: `Invalid province code: ${provinceCode}`,
      })
    }

    // Validate type digit (position 3: 0, 1, 6, 9)
    const typeDigit = parseInt(ruc.charAt(2), 10)
    if (![0, 1, 6, 9].includes(typeDigit)) {
      errors.push({
        code: 'INVALID_TAX_ID_FORMAT',
        message: `Invalid RUC type digit: ${typeDigit} (must be 0, 1, 6, or 9)`,
      })
    }

    // Validate checksum (modulo 11)
    if (!this._validateRUCChecksum(ruc)) {
      errors.push({
        code: 'INVALID_CHECKSUM',
        message: 'Invalid RUC checksum',
      })
    }

    return errors
  }

  /**
   * Validates RUC checksum using modulo 11 algorithm
   * Algorithm based on Ecuador SRI (Servicio de Rentas Internas)
   * @private
   */
  private static _validateRUCChecksum(ruc: string): boolean {
    if (ruc.length !== 13) return false

    // Weights for digits 1-9 (0-indexed: 0-8)
    const weights = [3, 2, 7, 6, 5, 4, 3, 2, 7]

    // Calculate sum for first 9 digits
    let total = 0
    for (let i = 0; i < 9; i++) {
      total += parseInt(ruc[i], 10) * weights[i]
    }

    const remainder = total % 11

    // Calculate expected check digit
    let checkDigit = remainder === 0 ? 0 : 11 - remainder
    if (checkDigit === 11) {
      checkDigit = 0
    }

    // Verify against position 10 (0-indexed: 9)
    return parseInt(ruc[9], 10) === checkDigit
  }

  /**
   * Validates Ecuador Clave de Acceso (access key)
   *
   * Format: 49 digits
   * Structure: DDMMYY + RUC(13) + Establishment(3) + Emission(3) + Sequential(9) + Type(2) + Checksum(1)
   */
  static validateEcuadorClaveAcceso(clave: string): ValidationError[] {
    const errors: ValidationError[] = []

    if (!clave) {
      return [{ code: 'EMPTY_VALUE', message: 'Clave de Acceso cannot be empty' }]
    }

    if (clave.length !== 49) {
      errors.push({
        code: 'INVALID_CLAVE_FORMAT',
        message: `Clave de Acceso must be 49 digits, got ${clave.length}`,
      })
      return errors
    }

    if (!/^\d+$/.test(clave)) {
      errors.push({
        code: 'INVALID_CLAVE_FORMAT',
        message: 'Clave de Acceso must contain only digits',
      })
      return errors
    }

    // Validate date (DDMMYY format in positions 1-6)
    const day = parseInt(clave.substring(0, 2), 10)
    const month = parseInt(clave.substring(2, 4), 10)

    if (day < 1 || day > 31) {
      errors.push({
        code: 'INVALID_DATE',
        message: `Invalid day: ${day}`,
      })
    }

    if (month < 1 || month > 12) {
      errors.push({
        code: 'INVALID_DATE',
        message: `Invalid month: ${month}`,
      })
    }

    return errors
  }

  /**
   * Validates Argentina CUIT (Código Único de Identificación Tributaria)
   *
   * Format: 11 digits with format XX-XXXXXXXX-X
   * Verifier digit calculated using modulo 11
   */
  static validateArgentinaCUIT(cuit: string): ValidationError[] {
    const errors: ValidationError[] = []

    if (!cuit) {
      return [{ code: 'EMPTY_VALUE', message: 'CUIT cannot be empty' }]
    }

    // Remove hyphens
    const cleanCUIT = cuit.replace(/-/g, '')

    if (!/^\d+$/.test(cleanCUIT)) {
      errors.push({
        code: 'INVALID_CUIT_FORMAT',
        message: 'CUIT must contain only digits (hyphens will be removed)',
      })
      return errors
    }

    if (cleanCUIT.length !== 11) {
      errors.push({
        code: 'INVALID_CUIT_FORMAT',
        message: `CUIT must be 11 digits, got ${cleanCUIT.length}`,
      })
      return errors
    }

    // First digit must be 2 or 2 (type: PJ)
    const typeDigit = parseInt(cleanCUIT.charAt(0), 10)
    if (![2, 23, 24, 25, 26, 27].includes(typeDigit)) {
      errors.push({
        code: 'INVALID_CUIT_TYPE',
        message: `Invalid CUIT type digit: ${typeDigit}`,
      })
    }

    return errors
  }

  /**
   * Validates Spain NIF/CIF (Número de Identificación Fiscal)
   *
   * Format: 9 characters (8 digits + 1 letter for NIF, or letter + 7 digits + 1 letter for CIF)
   */
  static validateSpainNIF(nif: string): ValidationError[] {
    const errors: ValidationError[] = []

    if (!nif) {
      return [{ code: 'EMPTY_VALUE', message: 'NIF cannot be empty' }]
    }

    const cleanNIF = nif.toUpperCase().replace(/-/g, '')

    // NIF: 8 digits + 1 letter
    const nifPattern = /^\d{8}[A-Z]$/
    // CIF: 1 letter + 7 digits + 1 letter or digit
    const cifPattern = /^[A-HJ-NP-SU-V]\d{7}[0-9A-J]$/

    if (!nifPattern.test(cleanNIF) && !cifPattern.test(cleanNIF)) {
      errors.push({
        code: 'INVALID_NIF_FORMAT',
        message: 'NIF format invalid (expected: 8 digits + letter, or CIF format)',
      })
    }

    return errors
  }

  /**
   * Generic validator dispatcher for country-specific tax IDs
   */
  static validateTaxID(country: string, taxID: string): ValidationError[] {
    const upperCountry = country.toUpperCase()

    switch (upperCountry) {
      case 'EC':
        return this.validateEcuadorRUC(taxID)
      case 'AR':
        return this.validateArgentinaCUIT(taxID)
      case 'ES':
        return this.validateSpainNIF(taxID)
      default:
        // For unknown countries, just check if it's not empty
        return !taxID ? [{ code: 'EMPTY_VALUE', message: 'Tax ID cannot be empty' }] : []
    }
  }

  /**
   * Ecuador-specific: validate access key format
   */
  static validateAccessKey(country: string, key: string): ValidationError[] {
    if (country.toUpperCase() === 'EC') {
      return this.validateEcuadorClaveAcceso(key)
    }
    return !key ? [{ code: 'EMPTY_VALUE', message: 'Access key cannot be empty' }] : []
  }
}

export default CountryValidator
