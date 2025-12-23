import { env } from '../env'
import { apiFetch as sharedApiFetch, HttpError, type HttpOptions, setApiUrl, API_URL } from '@shared/httpTenant'

// Configure base URL once from tenant env and re-export shared client.
setApiUrl(env.apiUrl || '/api')

export { API_URL, HttpError, type HttpOptions }
export const apiFetch = sharedApiFetch
