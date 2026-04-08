import { describe, expect, it } from 'vitest'

import { normalizeLineItemPageGroups } from './DocumentDetail'

describe('normalizeLineItemPageGroups', () => {
  it('preserves column alignment between headers and headers_norm', () => {
    const groups = normalizeLineItemPageGroups({
      line_item_page_groups: [
        {
          source_page: 1,
          headers: ['item', 'codigo', 'descripcion', 'unidad', 'cantidad', 'p. unitario', 'importe'],
          headers_norm: ['', 'supplier_ref', 'concept', '', 'quantity', 'unit_price', 'total_price'],
          line_items: [
            {
              item: '1',
              supplier_ref: 'PRO-0050',
              concept: 'Aceite',
              quantity: '60,000 ml',
              unit_price: '$ 0.0034',
              total_price: '$ 204.00',
            },
          ],
        },
      ],
    })

    expect(groups).toHaveLength(1)
    expect(groups[0].headers).toEqual(['item', 'codigo', 'descripcion', 'unidad', 'cantidad', 'p. unitario', 'importe'])
    expect(groups[0].headers_norm).toEqual(['', 'supplier_ref', 'concept', '', 'quantity', 'unit_price', 'total_price'])
    expect(groups[0].headers).toHaveLength(groups[0].headers_norm.length)
    expect(groups[0].headers_norm[2]).toBe('concept')
  })
})
