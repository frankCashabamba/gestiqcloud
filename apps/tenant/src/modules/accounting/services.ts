import { apiFetch } from '../../lib/http'
import { TENANT_ACCOUNTING, TENANT_POS } from '@shared/endpoints'

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

export type CuentaMayorMovimiento = {
    fecha: string
    asiento_numero: string
    descripcion: string
    debe: number | string
    haber: number | string
    saldo: number | string
}

export type CuentaMayor = {
    cuenta_id: string
    cuenta_codigo: string
    cuenta_nombre: string
    fecha_desde: string
    fecha_hasta: string
    saldo_inicial: number | string
    movimientos: CuentaMayorMovimiento[]
    total_debe: number | string
    total_haber: number | string
    saldo_final: number | string
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
    has_journal_entry?: boolean
}

export async function listCuentas(): Promise<PlanCuenta[]> {
    const data = await apiFetch<PlanCuenta[] | { items?: PlanCuenta[] }>(TENANT_ACCOUNTING.chartOfAccounts.base)
    if (Array.isArray(data)) return data
    if (data && Array.isArray((data as any).items)) return (data as any).items as PlanCuenta[]
    return []
}

export async function getCuenta(id: string): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(TENANT_ACCOUNTING.chartOfAccounts.byId(id))
}

export async function createCuenta(data: Partial<PlanCuenta>): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(TENANT_ACCOUNTING.chartOfAccounts.base, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function updateCuenta(id: string, data: Partial<PlanCuenta>): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(TENANT_ACCOUNTING.chartOfAccounts.byId(id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function removeCuenta(id: string): Promise<void> {
    await apiFetch(TENANT_ACCOUNTING.chartOfAccounts.byId(id), { method: 'DELETE' })
}

export async function seedCuentas(force = false): Promise<{ created: number; skipped: number; message: string }> {
    return apiFetch(`${TENANT_ACCOUNTING.chartOfAccounts.seed}?force=${force}`, { method: 'POST' })
}

export async function getCuentaMayor(id: string, fechaDesde?: string, fechaHasta?: string): Promise<CuentaMayor> {
    const params = new URLSearchParams()
    if (fechaDesde) params.set('fecha_desde', fechaDesde)
    if (fechaHasta) params.set('fecha_hasta', fechaHasta)
    const qs = params.toString()
    return apiFetch<CuentaMayor>(`${TENANT_ACCOUNTING.chartOfAccounts.ledger(id)}${qs ? `?${qs}` : ''}`)
}

export async function listAsientos(): Promise<AsientoContable[]> {
    return apiFetch<AsientoContable[]>(TENANT_ACCOUNTING.transactions)
}

export async function getAsiento(id: string): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(TENANT_ACCOUNTING.journalEntries.byId(id))
}

export async function createAsiento(data: Partial<AsientoContable>): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(TENANT_ACCOUNTING.journalEntries.base, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function updateAsiento(id: string, data: Partial<AsientoContable>): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(TENANT_ACCOUNTING.journalEntries.byId(id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function removeAsiento(id: string): Promise<void> {
    // El backend no permite DELETE de asientos: se anulan vía /cancel (POST).
    await apiFetch(TENANT_ACCOUNTING.journalEntries.cancel(id), { method: 'POST' })
}

export async function postAsiento(id: string): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(TENANT_ACCOUNTING.journalEntries.post(id), {
        method: 'POST',
    })
}

// ============================================================================
// Reportes contables (nuevos endpoints /reports/*)
// ============================================================================

export type ReportAccountLine = {
    code: string
    name: string
    balance: number
}

export type ProfitLossReport = {
    date_from: string
    date_to: string
    income: ReportAccountLine[]
    expenses: ReportAccountLine[]
    total_income: number
    total_expenses: number
    net_result: number
    currency: string
}

export type BalanceSheetReport = {
    as_of_date: string
    assets: ReportAccountLine[]
    liabilities: ReportAccountLine[]
    equity: ReportAccountLine[]
    total_assets: number
    total_liabilities: number
    total_equity: number
    balanced: boolean
    currency: string
}

export async function getProfitLossReport(
    date_from: string,
    date_to: string,
    include_draft = false,
): Promise<ProfitLossReport> {
    const params = new URLSearchParams({ date_from, date_to })
    if (include_draft) params.set('include_draft', 'true')
    return apiFetch<ProfitLossReport>(
        `${TENANT_ACCOUNTING.reports.profitLoss}?${params.toString()}`,
    )
}

export async function getBalanceSheetReport(as_of_date?: string): Promise<BalanceSheetReport> {
    const params = new URLSearchParams()
    if (as_of_date) params.set('as_of_date', as_of_date)
    const qs = params.toString()
    return apiFetch<BalanceSheetReport>(
        `${TENANT_ACCOUNTING.reports.balanceSheet}${qs ? `?${qs}` : ''}`,
    )
}

// POS contable
export async function getPosAccountingSettings(): Promise<PosAccountingSettings> {
    return apiFetch<PosAccountingSettings>(TENANT_ACCOUNTING.pos.settings)
}

export async function savePosAccountingSettings(payload: PosAccountingSettings): Promise<PosAccountingSettings> {
    return apiFetch<PosAccountingSettings>(TENANT_ACCOUNTING.pos.settings, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
}

export async function listPaymentMethods(): Promise<PaymentMethod[]> {
    return apiFetch<PaymentMethod[]>(TENANT_ACCOUNTING.pos.paymentMethods)
}

export async function createPaymentMethod(payload: Partial<PaymentMethod>): Promise<PaymentMethod> {
    return apiFetch<PaymentMethod>(TENANT_ACCOUNTING.pos.paymentMethods, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
}

export async function updatePaymentMethod(id: string, payload: Partial<PaymentMethod>): Promise<PaymentMethod> {
    return apiFetch<PaymentMethod>(TENANT_ACCOUNTING.pos.paymentMethodById(id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
}

export async function deletePaymentMethod(id: string): Promise<void> {
    await apiFetch(TENANT_ACCOUNTING.pos.paymentMethodById(id), { method: 'DELETE' })
}

// POS daily counts (cierres de caja) y asiento contable manual
export async function listDailyCounts(limit: number = 10): Promise<DailyCount[]> {
    return apiFetch<DailyCount[]>(`${TENANT_POS.dailyCounts}?limit=${limit}`)
}

export async function generateAccountingForShift(shiftId: string): Promise<any> {
    return apiFetch(TENANT_POS.shiftAccounting(shiftId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    })
}
