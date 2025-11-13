/**
 * Types comunes usados en toda la API
 */

export type UUID = string

export type Timestamp = string

export type PaginationParams = {
  limit?: number
  offset?: number
  page?: number
  per_page?: number
}

export type PaginatedResponse<T> = {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export type SortParams = {
  sort_by?: string
  order?: 'asc' | 'desc'
}

export type FilterParams = {
  [key: string]: string | number | boolean | null | undefined
}

export type APIError = {
  detail: string
  code?: string
  field?: string
}

export type SuccessResponse = {
  message: string
  status: 'success' | 'ok'
}

export type Currency = 'USD' | 'EUR' | 'GBP' | 'COP' | 'MXN'

export type Country = 'US' | 'ES' | 'EC' | 'CO' | 'MX'

export type Status = 'active' | 'inactive' | 'archived'

export type Tenant = {
  id: UUID
  name: string
  slug: string
  country: Country
  currency: Currency
  settings: Record<string, unknown>
  created_at: Timestamp
  updated_at: Timestamp
}
