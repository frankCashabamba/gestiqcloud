/**
 * Utilidades monetarias para el módulo POS.
 *
 * El backend usa Decimal con 2-4 decimales de precisión. El frontend usa
 * `number` (IEEE 754 double), que acumula error en operaciones encadenadas
 * (ej. 0.1 + 0.2 === 0.30000000000000004).
 *
 * Para evitar discrepancias entre el total mostrado y el enviado a la API
 * (p. ej. en checkout / impresión / cierre de turno), todo cálculo monetario
 * debe pasar por `roundMoney` en sus puntos de salida.
 *
 * NOTA: usamos 2 decimales por compatibilidad con la columna
 * `pos_payments.amount NUMERIC(12, 2)`. Para precios unitarios de productos
 * (NUMERIC(12, 4)) usar `roundUnitPrice`.
 */

/**
 * Redondea a 2 decimales (centavos), evitando arrastre de error de float.
 */
export function roundMoney(value: number): number {
    if (!Number.isFinite(value)) return 0
    return Math.round(value * 100) / 100
}

/**
 * Redondea a 4 decimales — para precios unitarios y tasas de impuesto.
 * Coincide con `unit_price NUMERIC(12, 4)` y `tax_rate NUMERIC(6, 4)`.
 */
export function roundUnitPrice(value: number): number {
    if (!Number.isFinite(value)) return 0
    return Math.round(value * 10000) / 10000
}

/**
 * Redondea cantidades a 3 decimales — para `qty NUMERIC(12, 3)`.
 */
export function roundQty(value: number): number {
    if (!Number.isFinite(value)) return 0
    return Math.round(value * 1000) / 1000
}

/**
 * Calcula el total de una línea (qty * unit_price * (1 - discount%)) y
 * lo redondea a 2 decimales.
 */
export function computeLineTotal(
    qty: number,
    unitPrice: number,
    discountPct: number = 0,
): number {
    const subtotal = qty * unitPrice
    const discount = subtotal * (discountPct / 100)
    return roundMoney(subtotal - discount)
}
