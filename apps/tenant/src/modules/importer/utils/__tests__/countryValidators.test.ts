import { CountryValidator } from '../countryValidators'

describe('CountryValidator', () => {
  describe('validateEcuadorRUC', () => {
    it('should accept valid RUC', () => {
      // Real RUC from Ecuador (formato típico)
      const errors = CountryValidator.validateEcuadorRUC('1790084103004')
      expect(errors).toHaveLength(0)
    })

    it('should accept RUC with type digit 0 (natural)', () => {
      // Valid RUC with correct checksum
      const errors = CountryValidator.validateEcuadorRUC('0109000000010')
      expect(errors).toHaveLength(0)
    })

    it('should accept RUC with type digit 1 (juridical)', () => {
      // Valid RUC with correct checksum
      const errors = CountryValidator.validateEcuadorRUC('0110000000002')
      expect(errors).toHaveLength(0)
    })

    it('should accept RUC with type digit 6 (government)', () => {
      // Valid RUC with correct checksum
      const errors = CountryValidator.validateEcuadorRUC('0160000000000')
      expect(errors).toHaveLength(0)
    })

    it('should accept RUC with type digit 9 (temporary)', () => {
      // Valid RUC with correct checksum
      const errors = CountryValidator.validateEcuadorRUC('0190000000001')
      expect(errors).toHaveLength(0)
    })

    it('should reject RUC with invalid province (99)', () => {
      const errors = CountryValidator.validateEcuadorRUC('9999999999999')
      expect(errors.some(e => e.code === 'INVALID_TAX_ID_FORMAT')).toBe(true)
      expect(errors.some(e => e.message.includes('province'))).toBe(true)
    })

    it('should reject RUC with province 00', () => {
      const errors = CountryValidator.validateEcuadorRUC('0099999999999')
      expect(errors.some(e => e.code === 'INVALID_TAX_ID_FORMAT')).toBe(true)
    })

    it('should reject RUC with invalid type digit (5)', () => {
      const errors = CountryValidator.validateEcuadorRUC('0150000000001')
      expect(errors.some(e => e.code === 'INVALID_TAX_ID_FORMAT')).toBe(true)
      expect(errors.some(e => e.message.includes('type digit'))).toBe(true)
    })

    it('should reject RUC with invalid checksum', () => {
      // Real RUC: 1790084103004, change last digit to make it invalid
      const errors = CountryValidator.validateEcuadorRUC('1790084103999')
      expect(errors.some(e => e.code === 'INVALID_CHECKSUM')).toBe(true)
    })

    it('should reject empty RUC', () => {
      const errors = CountryValidator.validateEcuadorRUC('')
      expect(errors.some(e => e.code === 'EMPTY_VALUE')).toBe(true)
    })

    it('should reject RUC with letters', () => {
      const errors = CountryValidator.validateEcuadorRUC('179008410300A')
      expect(errors.some(e => e.code === 'INVALID_TAX_ID_FORMAT')).toBe(true)
    })

    it('should reject RUC with less than 13 digits', () => {
      const errors = CountryValidator.validateEcuadorRUC('17900841030')
      expect(errors.some(e => e.code === 'INVALID_TAX_ID_FORMAT')).toBe(true)
      expect(errors.some(e => e.message.includes('13 digits'))).toBe(true)
    })

    it('should reject RUC with more than 13 digits', () => {
      const errors = CountryValidator.validateEcuadorRUC('17900841030001')
      expect(errors.some(e => e.code === 'INVALID_TAX_ID_FORMAT')).toBe(true)
    })
  })

  describe('validateSpainNIF', () => {
    it('should accept valid NIF', () => {
      // Real NIF format: 8 digits + letter
      const errors = CountryValidator.validateSpainNIF('12345678Z')
      expect(errors).toHaveLength(0)
    })

    it('should accept valid NIF with hyphens', () => {
      const errors = CountryValidator.validateSpainNIF('12345678-Z')
      expect(errors).toHaveLength(0)
    })

    it('should accept valid CIF', () => {
      // CIF format: 1 letter + 7 digits + 1 letter/digit
      const errors = CountryValidator.validateSpainNIF('A12345674')
      expect(errors).toHaveLength(0)
    })

    it('should reject NIF with invalid checksum letter', () => {
      const errors = CountryValidator.validateSpainNIF('12345678A')
      expect(errors.length).toBeGreaterThan(0)
    })

    it('should reject empty NIF', () => {
      const errors = CountryValidator.validateSpainNIF('')
      expect(errors.some(e => e.code === 'EMPTY_VALUE')).toBe(true)
    })

    it('should reject NIF with invalid format', () => {
      const errors = CountryValidator.validateSpainNIF('123')
      expect(errors.length).toBeGreaterThan(0)
    })
  })

  describe('validateArgentinaCUIT', () => {
    it('should accept valid CUIT', () => {
      // CUIT format: 11 digits, with modulo 11 checksum
      const errors = CountryValidator.validateArgentinaCUIT('20309108605')
      expect(errors).toHaveLength(0)
    })

    it('should accept CUIT with hyphens', () => {
      const errors = CountryValidator.validateArgentinaCUIT('20-30910860-5')
      expect(errors).toHaveLength(0)
    })

    it('should reject CUIT with invalid type digit', () => {
      // First digit should be 2 or 23-27
      const errors = CountryValidator.validateArgentinaCUIT('30309108605')
      expect(errors.some(e => e.code === 'INVALID_CUIT_TYPE')).toBe(true)
    })

    it('should reject CUIT with less than 11 digits', () => {
      const errors = CountryValidator.validateArgentinaCUIT('203091086')
      expect(errors.some(e => e.code === 'INVALID_CUIT_FORMAT')).toBe(true)
    })

    it('should reject empty CUIT', () => {
      const errors = CountryValidator.validateArgentinaCUIT('')
      expect(errors.some(e => e.code === 'EMPTY_VALUE')).toBe(true)
    })
  })

  describe('validateTaxID dispatcher', () => {
    it('should delegate Ecuador validation', () => {
      const errors = CountryValidator.validateTaxID('EC', '1790084103004')
      expect(errors).toHaveLength(0)
    })

    it('should delegate Spain validation', () => {
      const errors = CountryValidator.validateTaxID('ES', '12345678Z')
      expect(errors).toHaveLength(0)
    })

    it('should delegate Argentina validation', () => {
      const errors = CountryValidator.validateTaxID('AR', '20309108605')
      expect(errors).toHaveLength(0)
    })

    it('should accept unknown countries without validation', () => {
      const errors = CountryValidator.validateTaxID('XX', '123')
      expect(errors).toHaveLength(0)
    })

    it('should reject empty tax ID for unknown country', () => {
      const errors = CountryValidator.validateTaxID('XX', '')
      expect(errors.some(e => e.code === 'EMPTY_VALUE')).toBe(true)
    })
  })

  describe('validateAccessKey (Clave de Acceso)', () => {
    it('should accept valid Clave de Acceso', () => {
      // 49 digits: DDMMYY + RUC(13) + Establishment(3) + Emission(3) + Sequential(9) + Type(2) + Checksum(1)
      const clave = '1704201717900841030014001000000000011062021234567890'
      const errors = CountryValidator.validateAccessKey('EC', clave)
      expect(errors.filter(e => e.code === 'INVALID_CLAVE_FORMAT')).toHaveLength(0)
    })

    it('should reject Clave with invalid length', () => {
      const errors = CountryValidator.validateAccessKey('EC', '123')
      expect(errors.some(e => e.code === 'INVALID_CLAVE_FORMAT')).toBe(true)
    })

    it('should reject Clave with invalid date', () => {
      // Invalid day 99
      const clave = '9904201717900841030014001000000000011062021234567890'
      const errors = CountryValidator.validateAccessKey('EC', clave)
      expect(errors.some(e => e.code === 'INVALID_DATE')).toBe(true)
    })

    it('should reject Clave with invalid month', () => {
      // Invalid month 13
      const clave = '0113201717900841030014001000000000011062021234567890'
      const errors = CountryValidator.validateAccessKey('EC', clave)
      expect(errors.some(e => e.code === 'INVALID_DATE')).toBe(true)
    })

    it('should not validate Clave for non-Ecuador countries', () => {
      const errors = CountryValidator.validateAccessKey('ES', '123')
      expect(errors).toHaveLength(0)
    })
  })
})
