/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_BASE_PATH: string
  readonly VITE_TENANT_ORIGIN: string
  readonly VITE_ADMIN_ORIGIN: string
  readonly VITE_IMPORTS_JOB_POLL_INTERVAL?: string
  readonly VITE_IMPORTS_JOB_POLL_ATTEMPTS?: string
  readonly VITE_IMPORTS_JOB_RECHECK_INTERVAL?: string
  readonly VITE_IMPORTS_STORE_UPLOAD_FILES?: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
