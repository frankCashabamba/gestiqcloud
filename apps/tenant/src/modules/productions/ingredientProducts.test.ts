import { describe, expect, it } from 'vitest'
import { mergeIngredientProducts } from './ingredientProducts'

describe('mergeIngredientProducts', () => {
  it('keeps raw materials first and preserves already selected fallback products', () => {
    const merged = mergeIngredientProducts(
      [
        { id: 'raw-2', name: 'Azucar', unit: 'kg' } as any,
        { id: 'raw-1', name: 'Harina', unit: 'kg' } as any,
      ],
      [
        { id: 'final-1', name: 'Pan Final', unit: 'uds' } as any,
        { id: 'raw-1', name: 'Harina duplicada', unit: 'g' } as any,
      ],
      ['final-1'],
    )

    expect(merged.map((item) => item.id)).toEqual(['raw-2', 'raw-1', 'final-1'])
    expect(merged.find((item) => item.id === 'final-1')?.unit).toBe('uds')
  })

  it('ignores fallback products that are not already preferred', () => {
    const merged = mergeIngredientProducts(
      [{ id: 'raw-1', name: 'Harina', unit: 'kg' } as any],
      [{ id: 'final-1', name: 'Pan Final', unit: 'uds' } as any],
    )

    expect(merged.map((item) => item.id)).toEqual(['raw-1'])
  })
})
