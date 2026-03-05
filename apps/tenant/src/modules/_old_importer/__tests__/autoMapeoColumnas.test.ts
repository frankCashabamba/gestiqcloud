import { autoMapeoColumnas } from '../services/autoMapeoColumnas'

describe('autoMapeoColumnas', () => {
  it('mapea headers usando aliases proporcionados', () => {
    const headers = ['Nombre', 'Precio Unitario', 'SKU', 'Categoria']
    const alias = {
      nombre: ['nombre'],
      precio: ['precio unitario', 'precio'],
      sku: ['sku', 'codigo'],
    }

    const result = autoMapeoColumnas(headers, alias)

    expect(result).toEqual({
      nombre: 'Nombre',
      precio: 'Precio Unitario',
      sku: 'SKU',
    })
  })
})
