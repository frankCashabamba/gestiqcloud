import { apiFetch } from '../../lib/http'

export type PlanCuenta = {
    id: string
    codigo: string
    nombre: string
    tipo: 'ACTIVO' | 'PASIVO' | 'PATRIMONIO' | 'INGRESO' | 'GASTO'
    nivel: number
    padre_id?: string | null
    activo: boolean
    created_at?: string
    updated_at?: string
}

export type AsientoContable = {
    id: string
    numero: string
    fecha: string
    descripcion: string
    total_debe: number
    total_haber: number
    status: 'DRAFT' | 'POSTED' | 'VOIDED'
    lineas?: AsientoLinea[]
    created_at?: string
    updated_at?: string
}

export type AsientoLinea = {
    id: string
    asiento_id: string
    cuenta_id: string
    debe: number
    haber: number
    descripcion?: string
}

// =========================
// POS Contable (config)
// =========================

export type PosAccountingSettings = {
    cash_account_id: string
    bank_account_id: string
    sales_bakery_account_id?: string | null
    vat_output_account_id: string
    loss_account_id?: string | null
}

export type PaymentMethod = {
    id: string
    name: string
    description?: string | null
    account_id: string
    is_active: boolean
}

export type DailyCount = {
    id: string
    register_id: string
    shift_id: string
    count_date: string
    total_sales: number
    cash_sales?: number | null
    card_sales?: number | null
    other_sales?: number | null
    counted_cash?: number | null
    discrepancy?: number | null
}

export async function listCuentas(): Promise<PlanCuenta[]> {
    const data = await apiFetch<PlanCuenta[] | { items?: PlanCuenta[] }>('/api/v1/tenant/accounting/chart-of-accounts')
    if (Array.isArray(data)) return data
    if (data && Array.isArray((data as any).items)) return (data as any).items as PlanCuenta[]
    return []
}

export async function getCuenta(id: string): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(`/api/v1/tenant/accounting/chart-of-accounts/${id}`)
}

export async function createCuenta(data: Partial<PlanCuenta>): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>('/api/v1/tenant/accounting/chart-of-accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function updateCuenta(id: string, data: Partial<PlanCuenta>): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(`/api/v1/tenant/accounting/chart-of-accounts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function removeCuenta(id: string): Promise<void> {
    await apiFetch(`/api/v1/tenant/accounting/chart-of-accounts/${id}`, { method: 'DELETE' })
}

export async function listAsientos(): Promise<AsientoContable[]> {
    return apiFetch<AsientoContable[]>('/api/v1/tenant/accounting/transactions')
}

export async function getAsiento(id: string): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(`/api/v1/accounting/journal-entries/${id}`)
}

export async function createAsiento(data: Partial<AsientoContable>): Promise<AsientoContable> {
    return apiFetch<AsientoContable>('/api/v1/accounting/journal-entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function updateAsiento(id: string, data: Partial<AsientoContable>): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(`/api/v1/accounting/journal-entries/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function removeAsiento(id: string): Promise<void> {
    await apiFetch(`/api/v1/accounting/journal-entries/${id}`, { method: 'DELETE' })
}

export async function postAsiento(id: string): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(`/api/v1/accounting/journal-entries/${id}/post`, {
        method: 'POST',
    })
}

export async function getBalance(fecha: string): Promise<any> {
    return apiFetch(`/api/v1/accounting/balance?fecha=${fecha}`)
}

export async function getPyG(fecha_desde: string, fecha_hasta: string): Promise<any> {
    return apiFetch(`/api/v1/accounting/profit-loss?fecha_desde=${fecha_desde}&fecha_hasta=${fecha_hasta}`)
}

// POS contable
export async function getPosAccountingSettings(): Promise<PosAccountingSettings> {
    return apiFetch<PosAccountingSettings>('/api/v1/tenant/accounting/pos/settings')
}

export async function savePosAccountingSettings(payload: PosAccountingSettings): Promise<PosAccountingSettings> {
    return apiFetch<PosAccountingSettings>('/api/v1/tenant/accounting/pos/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
}

export async function listPaymentMethods(): Promise<PaymentMethod[]> {
    return apiFetch<PaymentMethod[]>('/api/v1/tenant/accounting/pos/payment-methods')
}

export async function createPaymentMethod(payload: Partial<PaymentMethod>): Promise<PaymentMethod> {
    return apiFetch<PaymentMethod>('/api/v1/tenant/accounting/pos/payment-methods', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
}

export async function updatePaymentMethod(id: string, payload: Partial<PaymentMethod>): Promise<PaymentMethod> {
    return apiFetch<PaymentMethod>(`/api/v1/tenant/accounting/pos/payment-methods/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
}

export async function deletePaymentMethod(id: string): Promise<void> {
    await apiFetch(`/api/v1/tenant/accounting/pos/payment-methods/${id}`, { method: 'DELETE' })
}

// POS daily counts (cierres de caja) y asiento contable manual
export async function listDailyCounts(limit: number = 10): Promise<DailyCount[]> {
    return apiFetch<DailyCount[]>(`/api/v1/tenant/pos/daily_counts?limit=${limit}`)
}

export async function generateAccountingForShift(shiftId: string): Promise<any> {
    return apiFetch(`/api/v1/tenant/pos/shifts/${shiftId}/accounting`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    })
}
