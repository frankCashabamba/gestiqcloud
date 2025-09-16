import type { AxiosInstance } from 'axios'

export function createOnboardingService(api: AxiosInstance, basePath: string) {
  return {
    enviarConfiguracionInicial: async <T = any>(payload: any) => {
      const { data } = await api.post<T>(basePath, payload)
      return data
    },
  }
}

