import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { POSKeyboardHelp } from './POSKeyboardHelp'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const map: Record<string, string> = {
        'pos:keyboard.searchProduct': 'Buscar producto',
        'pos:keyboard.selectCustomer': 'Seleccionar cliente',
        'pos:keyboard.globalDiscount': 'Descuento global',
        'pos:keyboard.suspendSale': 'Suspender venta',
        'pos:keyboard.openPayment': 'Abrir pago',
        'pos:keyboard.confirmPayment': 'Confirmar pago',
        'pos:keyboard.closeModal': 'Cerrar modal',
        'pos:keyboard.navigateLists': 'Navegar',
        'pos:keyboard.shortcutsButton': 'Atajos de teclado',
        'pos:keyboard.title': 'Atajos de Teclado',
        'pos:keyboard.tip': 'Consejo',
        'pos:keyboard.bakeryShortcutKey': 'Letra',
        'pos:keyboard.bakeryShortcutDescription': 'Agrega 1 conjunto al instante',
        'common:close': 'Cerrar',
      }

      if (key === 'pos:keyboard.bakeryShortcutItem') {
        return `${options?.product} · ${options?.quantity} uds por $${options?.price}`
      }

      return map[key] ?? key
    },
    i18n: { changeLanguage: vi.fn() },
  }),
}))

describe('POSKeyboardHelp', () => {
  it('shows the simplified bakery shortcut guidance', () => {
    render(
      <POSKeyboardHelp
        bulkPricingItems={[
          {
            product_id: 'pan-tapado',
            product_name: 'PAN TAPADO',
            quantity: 6,
            unit_price: 1,
            shortcut_letter: 'T',
          },
        ]}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Atajos de teclado' }))

    expect(screen.getByText('Letra')).toBeInTheDocument()
    expect(screen.getByText('Agrega 1 conjunto al instante')).toBeInTheDocument()
    expect(screen.getByText('T')).toBeInTheDocument()
    expect(screen.getByText('PAN TAPADO · 6 uds por $1.00')).toBeInTheDocument()
  })
})
