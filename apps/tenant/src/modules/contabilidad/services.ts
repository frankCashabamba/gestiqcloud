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

export async function listCuentas(): Promise<PlanCuenta[]> {
    return apiFetch<PlanCuenta[]>('/api/v1/accounting/cuentas')
}

export async function getCuenta(id: string): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(`/api/v1/accounting/cuentas/${id}`)
}

export async function createCuenta(data: Partial<PlanCuenta>): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>('/api/v1/accounting/cuentas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function updateCuenta(id: string, data: Partial<PlanCuenta>): Promise<PlanCuenta> {
    return apiFetch<PlanCuenta>(`/api/v1/accounting/cuentas/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function removeCuenta(id: string): Promise<void> {
    await apiFetch(`/api/v1/accounting/cuentas/${id}`, { method: 'DELETE' })
}

export async function listAsientos(): Promise<AsientoContable[]> {
    return apiFetch<AsientoContable[]>('/api/v1/accounting/asientos')
}

export async function getAsiento(id: string): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(`/api/v1/accounting/asientos/${id}`)
}

export async function createAsiento(data: Partial<AsientoContable>): Promise<AsientoContable> {
    return apiFetch<AsientoContable>('/api/v1/accounting/asientos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function updateAsiento(id: string, data: Partial<AsientoContable>): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(`/api/v1/accounting/asientos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
}

export async function removeAsiento(id: string): Promise<void> {
    await apiFetch(`/api/v1/accounting/asientos/${id}`, { method: 'DELETE' })
}

export async function postAsiento(id: string): Promise<AsientoContable> {
    return apiFetch<AsientoContable>(`/api/v1/accounting/asientos/${id}/post`, {
        method: 'POST',
    })
}

export async function getBalance(fecha: string): Promise<any> {
    return apiFetch(`/api/v1/accounting/balance?fecha=${fecha}`)
}

export async function getPyG(fecha_desde: string, fecha_hasta: string): Promise<any> {
    return apiFetch(`/api/v1/accounting/perdidas-ganancias?fecha_desde=${fecha_desde}&fecha_hasta=${fecha_hasta}`)
}
