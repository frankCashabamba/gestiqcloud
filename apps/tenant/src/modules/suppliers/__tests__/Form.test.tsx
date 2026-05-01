import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// --- Mocks ----------------------------------------------------------------

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

const updateProveedorMock = vi.fn()
const createProveedorMock = vi.fn()
const getProveedorMock = vi.fn()

vi.mock('../services', async () => {
  return {
    updateProveedor: (...args: any[]) => updateProveedorMock(...args),
    createProveedor: (...args: any[]) => createProveedorMock(...args),
    getProveedor: (...args: any[]) => getProveedorMock(...args),
  }
})

vi.mock('../../../shared/toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
  getErrorMessage: (e: any) => String(e?.message || e),
}))

vi.mock('../../../hooks/useGlobalCatalogs', () => ({
  useCountries: () => ({ items: [{ code: 'ES', name: 'España' }] }),
  useTaxTypes: () => ({ items: [{ code: 'IVA', name: 'IVA' }] }),
}))

// --- Tests ----------------------------------------------------------------

import ProveedorForm from '../Form'

const baseProveedor = {
  id: 'sup-1',
  name: 'ACME',
  nombre_comercial: null,
  nif: null,
  pais: 'ES',
  idioma: 'es',
  email: null,
  phone: null,
  tipo_impuesto: 'IVA',
  retencion_irpf: null,
  exento_impuestos: false,
  regimen_especial: null,
  condiciones_pago: null,
  plazo_pago_dias: 30,
  descuento_pronto_pago: null,
  divisa: null,
  metodo_pago: null,
  iban: 'ES0000000000000000000000',
  contactos: [],
  direcciones: [],
}

function renderEdit() {
  return render(
    <MemoryRouter initialEntries={['/suppliers/sup-1/edit']}>
      <Routes>
        <Route path="/suppliers/:id/edit" element={<ProveedorForm />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProveedorForm — IBAN payload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getProveedorMock.mockResolvedValue(baseProveedor)
    updateProveedorMock.mockResolvedValue(baseProveedor)
  })

  it('envía iban_confirmation en el payload del PUT cuando cambia el IBAN', async () => {
    renderEdit()
    // Wait for the form to load
    await waitFor(() => expect(getProveedorMock).toHaveBeenCalled())
    await screen.findByDisplayValue('ACME')

    // Change IBAN and confirm IBAN to a new matching value
    const ibanInputs = screen.getAllByPlaceholderText('ES00 0000 0000 0000 0000 0000')
    expect(ibanInputs).toHaveLength(2)
    const [ibanInput, confirmInput] = ibanInputs

    fireEvent.change(ibanInput, { target: { value: 'ES1111111111111111111111' } })
    fireEvent.change(confirmInput, { target: { value: 'ES1111111111111111111111' } })

    // Submit the form
    const form = ibanInput.closest('form')!
    fireEvent.submit(form)

    await waitFor(() => expect(updateProveedorMock).toHaveBeenCalled())
    const [, payload] = updateProveedorMock.mock.calls[0]
    expect(payload.iban).toBe('ES1111111111111111111111')
    // Backend expects English field name AND it must NOT be stripped client-side
    expect(payload.iban_confirmation).toBe('ES1111111111111111111111')
    expect(payload).not.toHaveProperty('iban_confirmacion')
  })
})
