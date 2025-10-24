export function detectarTipoDocumento(headers: string[]): 'generico' | 'factura' | 'recibo' | 'transferencia' {
  const h = headers.map(x => x.toLowerCase())
  if (h.includes('invoice') || h.includes('nro_factura') || h.includes('cliente')) return 'factura'
  if (h.includes('recibo') || h.includes('empleado')) return 'recibo'
  if (h.includes('banco') || h.includes('iban') || h.includes('transferencia')) return 'transferencia'
  return 'generico'
}

