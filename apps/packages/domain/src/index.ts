import type { AxiosInstance } from '@shared/http'

type ServiceOpts = { base: string }

export function createEmpresaService(api: AxiosInstance, opts: ServiceOpts) {
  const base = opts.base || '/api/v1/admin/empresas'
  return {
    async getEmpresas<T = any[]>(): Promise<T> {
      const r = await api.get<T>(base)
      return r.data
    },
    async createEmpresa<T = any>(payload: any): Promise<T> {
      const r = await api.post<T>(base, payload)
      return r.data
    },
    async updateEmpresa<T = any>(id: number | string, payload: any): Promise<T> {
      const r = await api.put<T>(`${base}/${id}`, payload)
      return r.data
    },
    async deleteEmpresa<T = any>(id: number | string): Promise<T> {
      const r = await api.delete<T>(`${base}/${id}`)
      return r.data
    },
  }
}
