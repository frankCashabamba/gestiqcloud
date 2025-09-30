/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_BASE_PATH: string
  readonly VITE_TENANT_ORIGIN: string
  readonly VITE_ADMIN_ORIGIN: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
