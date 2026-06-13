import { describe, expect, it } from 'vitest'
import { normalizePermissions, splitPermissionKey } from './PermissionsContext'

describe('PermissionsContext permission normalization', () => {
  it('splits both colon and dotted permissions by the last separator', () => {
    expect(splitPermissionKey('billing:create')).toEqual({ module: 'billing', action: 'create' })
    expect(splitPermissionKey('pos.receipt.pay')).toEqual({ module: 'pos.receipt', action: 'pay' })
  })

  it('aliases backend POS dotted permissions to frontend route permissions', () => {
    const normalized = normalizePermissions({
      'pos.view': true,
      'pos.receipt.pay': true,
      'pos.shift.close': true,
      'pos.receipt.refund': true,
    })

    expect(normalized.pos?.read).toBe(true)
    expect(normalized.pos?.cashier).toBe(true)
    expect(normalized.pos?.close_shift).toBe(true)
    expect(normalized.pos?.refund).toBe(true)
  })

  it('aliases frontend accounting and quote permissions to backend dotted permissions', () => {
    const normalized = normalizePermissions({
      'accounting:entry': true,
      'quotes:update': true,
    })

    expect(normalized.accounting?.entry).toBe(true)
    expect(normalized['accounting.entry']?.create).toBe(true)
    expect(normalized.quotes?.update).toBe(true)
    expect(normalized.quotes?.manage).toBe(true)
  })

  it('keeps legacy template and webhook aliases available', () => {
    const normalized = normalizePermissions({
      'read:templates': true,
      'admin:webhooks': true,
    })

    expect(normalized.templates?.manage).toBe(true)
    expect(normalized.webhooks?.manage).toBe(true)
  })
})
