import api from "../../services/api"

export interface CountryPack {
  id?: string
  code: string
  name: string
  region: string
  validators?: Record<string, any>
  tax_rules?: Record<string, any>
  currency?: string
  active?: boolean
}

export async function listCountryPacks(): Promise<CountryPack[]> {
  return api.get('/country-packs').then((r: { data: CountryPack[] }) => r.data)
}

export async function getCountryPack(code: string): Promise<CountryPack> {
  return api.get(`/country-packs/${code}`).then((r: { data: CountryPack }) => r.data)
}

export async function createCountryPack(payload: CountryPack): Promise<CountryPack> {
  return api.post('/country-packs', payload).then((r: { data: CountryPack }) => r.data)
}

export async function updateCountryPack(code: string, payload: Partial<CountryPack>): Promise<CountryPack> {
  return api.patch(`/country-packs/${code}`, payload).then((r: { data: CountryPack }) => r.data)
}

export async function deleteCountryPack(code: string): Promise<void> {
  return api.delete(`/country-packs/${code}`).then((r: { data: void }) => r.data)
}

export async function validateCountryConfig(code: string, config: Record<string, unknown>): Promise<{ valid: boolean; errors?: string[] }> {
  return api.post(`/country-packs/${code}/validate`, config).then((r: { data: { valid: boolean; errors?: string[] } }) => r.data)
}
