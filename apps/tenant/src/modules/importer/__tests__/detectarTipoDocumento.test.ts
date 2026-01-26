import { detectarTipoDocumento } from '../utils/detectarTipoDocumento'

describe('detectarTipoDocumento', () => {
  it('detecta products por SKU y nombre', () => {
    const tipo = detectarTipoDocumento(['SKU', 'Nombre', 'Precio'])
    expect(tipo).toBe('products')
  })

  it('detecta invoices por campos fiscales', () => {
    const tipo = detectarTipoDocumento(['Factura', 'NIF', 'Total'])
    expect(tipo).toBe('invoices')
  })

  it('detecta bank por referencia bancaria', () => {
    const tipo = detectarTipoDocumento(['IBAN', 'Amount'])
    expect(tipo).toBe('bank')
  })

  it('cae a expenses como fallback', () => {
    const tipo = detectarTipoDocumento(['Empleado', 'Concepto'])
    expect(tipo).toBe('expenses')
  })
})
