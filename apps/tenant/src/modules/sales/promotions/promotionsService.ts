import tenantApi from '../../../shared/api/client'
import { TENANT_PROMOTIONS } from '@shared/endpoints'

export type PromotionType = 'percentage' | 'fixed' | 'bogo'
export type PromotionAppliesTo = 'all' | 'products'

export type Promotion = {
  id: string
  tenant_id: string
  name: string
  description?: string
  type: PromotionType
  value: number
  valid_from?: string
  valid_to?: string
  min_purchase: number
  applies_to: PromotionAppliesTo
  product_ids?: string[]
  promo_code?: string
  is_active: boolean
  usage_limit?: number
  usage_count: number
  created_at?: string
  updated_at?: string
}

export type PromotionIn = Omit<Promotion, 'id' | 'tenant_id' | 'usage_count' | 'created_at' | 'updated_at'>

export type ValidateResult = {
  valid: boolean
  promotion_id?: string
  discount_amount: number
  message: string
}

export type PromotionStatus = 'active' | 'scheduled' | 'expired' | 'inactive'

export function getPromotionStatus(p: Promotion): PromotionStatus {
  if (!p.is_active) return 'inactive'
  const today = new Date().toISOString().slice(0, 10)
  if (p.valid_from && today < p.valid_from) return 'scheduled'
  if (p.valid_to && today > p.valid_to) return 'expired'
  return 'active'
}

export async function listPromotions(isActive?: boolean): Promise<Promotion[]> {
  const params = isActive !== undefined ? `?is_active=${isActive}` : ''
  const { data } = await tenantApi.get<Promotion[]>(`${TENANT_PROMOTIONS.base}${params}`)
  return Array.isArray(data) ? data : []
}

export async function getPromotion(id: string): Promise<Promotion> {
  const { data } = await tenantApi.get<Promotion>(TENANT_PROMOTIONS.byId(id))
  return data
}

export async function createPromotion(payload: PromotionIn): Promise<Promotion> {
  const { data } = await tenantApi.post<Promotion>(TENANT_PROMOTIONS.base, payload)
  return data
}

export async function updatePromotion(id: string, payload: PromotionIn): Promise<Promotion> {
  const { data } = await tenantApi.put<Promotion>(TENANT_PROMOTIONS.byId(id), payload)
  return data
}

export async function removePromotion(id: string): Promise<void> {
  await tenantApi.delete(TENANT_PROMOTIONS.byId(id))
}

export async function validatePromoCode(code: string, cartTotal: number): Promise<ValidateResult> {
  const { data } = await tenantApi.post<ValidateResult>(TENANT_PROMOTIONS.validate, {
    code,
    cart_total: cartTotal,
  })
  return data
}
