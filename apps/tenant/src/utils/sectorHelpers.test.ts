/**
 * Tests for sectorHelpers utility functions
 */
import {
  getSectorIcon,
  getSectorColor,
  getSectorDisplayName,
  getSectorUnits,
  getSectorPrintConfig,
  formatBySector,
  isFieldRequired,
} from './sectorHelpers'

describe('sectorHelpers', () => {
  describe('getSectorIcon', () => {
    it('should return icon for panaderia', () => {
      expect(getSectorIcon('panaderia')).toBe('B')
    })

    it('should return icon for bakery (english)', () => {
      expect(getSectorIcon('bakery')).toBe('B')
    })

    it('should return icon for taller', () => {
      expect(getSectorIcon('taller')).toBe('T')
    })

    it('should return icon for retail', () => {
      expect(getSectorIcon('retail')).toBe('R')
    })

    it('should return default icon for unknown sector', () => {
      expect(getSectorIcon('unknown_sector')).toBe('G')
    })

    it('should handle sectors with dashes and underscores', () => {
      expect(getSectorIcon('taller-mecanico')).toBe('T')
      expect(getSectorIcon('taller_mecanico')).toBe('T')
    })
  })

  describe('getSectorColor', () => {
    it('should return color for panaderia', () => {
      expect(getSectorColor('panaderia')).toBe('#f59e0b')
    })

    it('should return color for taller', () => {
      expect(getSectorColor('taller')).toBe('#1e40af')
    })

    it('should return color for retail', () => {
      expect(getSectorColor('retail')).toBe('#059669')
    })

    it('should return default color for unknown sector', () => {
      expect(getSectorColor('unknown_sector')).toBe('#6366f1')
    })
  })

  describe('getSectorDisplayName', () => {
    it('should return display name for panaderia', () => {
      expect(getSectorDisplayName('panaderia')).toBe('Bakery')
    })

    it('should return display name for taller', () => {
      expect(getSectorDisplayName('taller')).toBe('Auto Shop')
    })

    it('should return display name for retail', () => {
      expect(getSectorDisplayName('retail')).toBe('Retail')
    })

    it('should capitalize unknown sectors', () => {
      const result = getSectorDisplayName('custom_sector')
      expect(result).toBe('Custom Sector')
    })
  })

  describe('getSectorUnits', () => {
    it('should return units for panaderia', () => {
      const units = getSectorUnits('panaderia')
      expect(Array.isArray(units)).toBe(true)
      expect(units.length).toBeGreaterThan(0)
    })

    it('should return units for taller', () => {
      const units = getSectorUnits('taller')
      expect(Array.isArray(units)).toBe(true)
      expect(units.some(u => u[0] === 'l')).toBe(true)
    })

    it('should return default units for unknown sector', () => {
      const units = getSectorUnits('unknown')
      expect(Array.isArray(units)).toBe(true)
      expect(units.length).toBeGreaterThan(0)
    })
  })

  describe('getSectorPrintConfig', () => {
    it('should return print config for panaderia', () => {
      const config = getSectorPrintConfig('panaderia')
      expect(config).toHaveProperty('width')
      expect(config).toHaveProperty('fontSize')
      expect(config).toHaveProperty('showLogo')
      expect(config).toHaveProperty('showDetails')
    })

    it('should return print config for taller', () => {
      const config = getSectorPrintConfig('taller')
      expect(config.width).toBe(80)
      expect(config.showDetails).toBe(true)
    })

    it('should return default print config for unknown sector', () => {
      const config = getSectorPrintConfig('unknown')
      expect(config.width).toBe(58)
    })
  })

  describe('formatBySector', () => {
    it('should format currency values', () => {
      const result = formatBySector(100.5, 'currency', 'retail', 'EUR')
      expect(result).toContain('100')
    })

    it('should format quantity for panaderia', () => {
      const result = formatBySector(5.5, 'quantity', 'panaderia')
      expect(result).toContain('5')
      expect(result).toContain('units')
    })

    it('should format weight for panaderia in grams', () => {
      const result = formatBySector(0.5, 'weight', 'panaderia')
      expect(result).toContain('g')
    })

    it('should format weight in kg', () => {
      const result = formatBySector(2.5, 'weight', 'panaderia')
      expect(result).toContain('kg')
    })

    it('should format percentage', () => {
      const result = formatBySector(25.5, 'percentage')
      expect(result).toBe('25.5%')
    })

    it('should return dash for null/undefined values', () => {
      expect(formatBySector(null, 'currency')).toBe('-')
      expect(formatBySector(undefined, 'currency')).toBe('-')
      expect(formatBySector('', 'currency')).toBe('-')
    })

    it('should format date', () => {
      const result = formatBySector('2024-01-15', 'date', 'retail')
      expect(result).toContain('15')
    })
  })

  describe('isFieldRequired', () => {
    it('should return true for expires_at in panaderia products', () => {
      expect(isFieldRequired('expires_at', 'panaderia', 'product')).toBe(true)
    })

    it('should return true for expires_at in panaderia inventory', () => {
      expect(isFieldRequired('expires_at', 'panaderia', 'inventory')).toBe(true)
    })

    it('should return true for sku in retail products', () => {
      expect(isFieldRequired('sku', 'retail', 'product')).toBe(true)
    })

    it('should return false for non-required fields', () => {
      expect(isFieldRequired('description', 'retail', 'product')).toBe(false)
    })

    it('should return false for codigo_oem in taller products', () => {
      expect(isFieldRequired('codigo_oem', 'taller', 'product')).toBe(false)
    })
  })
})
