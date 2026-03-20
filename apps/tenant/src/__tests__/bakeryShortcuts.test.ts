import { describe, expect, it } from 'vitest'

import {
  MAX_BAKERY_SHORTCUTS,
  getBakeryShortcutValidationError,
  normalizeBakeryShortcutLetter,
} from '../modules/pos/bakeryShortcuts'

describe('bakeryShortcuts', () => {
  it('normalizes shortcut letters to a single uppercase alpha character', () => {
    expect(normalizeBakeryShortcutLetter(' t ')).toBe('T')
    expect(normalizeBakeryShortcutLetter('ñ')).toBe('N')
    expect(normalizeBakeryShortcutLetter('12')).toBe('')
  })

  it('rejects duplicate letters and more than ten bakery shortcuts', () => {
    const tenItems = Array.from({ length: MAX_BAKERY_SHORTCUTS }, (_, index) => ({
      product_id: `p-${index}`,
      quantity: 8,
      unit_price: 1,
      shortcut_letter: String.fromCharCode(65 + index),
    }))

    expect(getBakeryShortcutValidationError(tenItems, 'A', 'otro')).toContain('ya esta asignada')
    expect(getBakeryShortcutValidationError(tenItems, 'K', 'otro')).toContain('Solo se permiten')
  })
})
