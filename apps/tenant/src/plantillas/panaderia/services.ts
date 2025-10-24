/**
 * Panadería Services - SPEC-1 API Integration
 */
import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'

// ============================================================================
// Types
// ============================================================================

export type DailyInventory = {
  id: string
  tenant_id: string
  product_id: string
  fecha: string
  stock_inicial: number
  venta_unidades: number
  stock_final: number
  ajuste: number
  precio_unitario_venta?: number
  importe_total?: number
  source_file?: string
  created_at: string
}

export type DailyInventoryCreate = {
  product_id: string
  fecha: string
  stock_inicial: number
  venta_unidades: number
  stock_final: number
  precio_unitario_venta?: number
}

export type Purchase = {
  id: string
  tenant_id: string
  fecha: string
  supplier_name?: string
  product_id?: string
  cantidad: number
  costo_unitario: number
  total?: number
  notas?: string
  created_at: string
}

export type PurchaseCreate = {
  fecha: string
  supplier_name?: string
  product_id?: string
  cantidad: number
  costo_unitario: number
  notas?: string
}

export type MilkRecord = {
  id: string
  tenant_id: string
  fecha: string
  litros: number
  grasa_pct?: number
  notas?: string
  created_at: string
}

export type MilkRecordCreate = {
  fecha: string
  litros: number
  grasa_pct?: number
  notas?: string
}

export type InventoryStats = {
  total_registros: number
  total_ventas_unidades: number
  total_ingresos: number
  registros_con_ajuste: number
  precio_promedio: number
}

export type PurchaseStats = {
  total_compras: number
  total_cantidad: number
  total_costo: number
  costo_promedio: number
}

export type MilkStats = {
  total_registros: number
  total_litros: number
  promedio_litros_dia: number
  promedio_grasa?: number
}

// ============================================================================
// Daily Inventory
// ============================================================================

const BASE_INVENTORY = '/api/v1/daily-inventory'

export async function listDailyInventory(params?: {
  fecha_desde?: string
  fecha_hasta?: string
  product_id?: string
  skip?: number
  limit?: number
}): Promise<DailyInventory[]> {
  const { data } = await tenantApi.get<DailyInventory[]>(BASE_INVENTORY, { params })
  return ensureArray<DailyInventory>(data)
}

export async function getDailyInventory(id: string): Promise<DailyInventory> {
  const { data } = await tenantApi.get<DailyInventory>(`${BASE_INVENTORY}/${id}`)
  return data
}

export async function createDailyInventory(payload: DailyInventoryCreate): Promise<DailyInventory> {
  const { data } = await tenantApi.post<DailyInventory>(BASE_INVENTORY, payload)
  return data
}

export async function updateDailyInventory(
  id: string,
  payload: Partial<DailyInventoryCreate>
): Promise<DailyInventory> {
  const { data } = await tenantApi.put<DailyInventory>(`${BASE_INVENTORY}/${id}`, payload)
  return data
}

export async function removeDailyInventory(id: string): Promise<void> {
  await tenantApi.delete(`${BASE_INVENTORY}/${id}`)
}

export async function getDailyInventoryStats(params?: {
  fecha_desde?: string
  fecha_hasta?: string
}): Promise<InventoryStats> {
  const { data } = await tenantApi.get<InventoryStats>(`${BASE_INVENTORY}/stats/summary`, { params })
  return data
}

// ============================================================================
// Purchases
// ============================================================================

const BASE_PURCHASES = '/api/v1/purchases'

export async function listPurchases(params?: {
  fecha_desde?: string
  fecha_hasta?: string
  supplier_name?: string
  product_id?: string
  skip?: number
  limit?: number
}): Promise<Purchase[]> {
  const { data } = await tenantApi.get<Purchase[]>(BASE_PURCHASES, { params })
  return ensureArray<Purchase>(data)
}

export async function getPurchase(id: string): Promise<Purchase> {
  const { data } = await tenantApi.get<Purchase>(`${BASE_PURCHASES}/${id}`)
  return data
}

export async function createPurchase(payload: PurchaseCreate): Promise<Purchase> {
  const { data } = await tenantApi.post<Purchase>(BASE_PURCHASES, payload)
  return data
}

export async function updatePurchase(id: string, payload: Partial<PurchaseCreate>): Promise<Purchase> {
  const { data } = await tenantApi.put<Purchase>(`${BASE_PURCHASES}/${id}`, payload)
  return data
}

export async function removePurchase(id: string): Promise<void> {
  await tenantApi.delete(`${BASE_PURCHASES}/${id}`)
}

export async function getPurchaseStats(params?: {
  fecha_desde?: string
  fecha_hasta?: string
  supplier_name?: string
}): Promise<PurchaseStats> {
  const { data } = await tenantApi.get<PurchaseStats>(`${BASE_PURCHASES}/stats/summary`, { params })
  return data
}

// ============================================================================
// Milk Records
// ============================================================================

const BASE_MILK = '/api/v1/milk-records'

export async function listMilkRecords(params?: {
  fecha_desde?: string
  fecha_hasta?: string
  skip?: number
  limit?: number
}): Promise<MilkRecord[]> {
  const { data } = await tenantApi.get<MilkRecord[]>(BASE_MILK, { params })
  return ensureArray<MilkRecord>(data)
}

export async function getMilkRecord(id: string): Promise<MilkRecord> {
  const { data } = await tenantApi.get<MilkRecord>(`${BASE_MILK}/${id}`)
  return data
}

export async function createMilkRecord(payload: MilkRecordCreate): Promise<MilkRecord> {
  const { data } = await tenantApi.post<MilkRecord>(BASE_MILK, payload)
  return data
}

export async function updateMilkRecord(id: string, payload: Partial<MilkRecordCreate>): Promise<MilkRecord> {
  const { data } = await tenantApi.put<MilkRecord>(`${BASE_MILK}/${id}`, payload)
  return data
}

export async function removeMilkRecord(id: string): Promise<void> {
  await tenantApi.delete(`${BASE_MILK}/${id}`)
}

export async function getMilkStats(params?: {
  fecha_desde?: string
  fecha_hasta?: string
}): Promise<MilkStats> {
  const { data } = await tenantApi.get<MilkStats>(`${BASE_MILK}/stats/summary`, { params })
  return data
}

// ============================================================================
// Excel Importer
// ============================================================================

const BASE_IMPORTER = '/api/v1/imports/spec1'

export type ImportResult = {
  success: boolean
  filename: string
  stats: {
    products_created: number
    products_updated: number
    daily_inventory_created: number
    daily_inventory_updated: number
    purchases_created: number
    milk_records_created: number
    sales_created: number
    errors: string[]
    warnings: string[]
  }
}

export async function importExcel(
  file: File,
  fechaManual?: string,
  simulateSales: boolean = true
): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  if (fechaManual) {
    formData.append('fecha_manual', fechaManual)
  }
  formData.append('simulate_sales', String(simulateSales))

  const { data } = await tenantApi.post<ImportResult>(`${BASE_IMPORTER}/excel`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

export async function getImportTemplate() {
  const { data } = await tenantApi.get(`${BASE_IMPORTER}/template`)
  return data
}
