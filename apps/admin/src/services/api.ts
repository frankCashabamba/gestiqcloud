// apps/admin/src/services/api.ts
// Bridge for legacy imports expecting './api' with an axios-like client
import api from '../utils/axios'

// Named alias for compatibility (e.g., sectorAdminConfig.ts expects apiClient)
export const apiClient = api

export default api
