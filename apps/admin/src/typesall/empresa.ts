export interface Empresa {
  id: number;
  nombre: string;
  name?: string;
  modulos?: string[];
}



export interface FormularioEmpresa {
  nombre_empresa: string;
  sector_plantilla_id?: number | null;
  ruc: string;
  telefono: string;
  direccion: string;
  pais: string;
  country_code?: string;
  provincia: string;
  ciudad: string;
  cp: string;
  sitio_web: string;
  logo: File | null;
  primaryColor: string;
  secondaryColor: string;
  startTemplate: string;
  /**
   * Raw textarea content. Must be parsed to an object before sending to the
   * backend. The wire payload uses {@link EmpresaPayload.config_json}, which
   * is a `Record<string, unknown>` (the backend rejects strings). See
   * `buildEmpresaPayload` in `utils/formToJson.ts`.
   */
  config_json: string;
  default_language?: string;
  timezone?: string;
  currency?: string;
  nombre_encargado: string;
  apellido_encargado: string;
  segundo_apellido_encargado?: string;
  email: string;
  username: string;
  password?: string;
  modulos: string[];
}

/**
 * Payload sent to POST/PUT /v1/admin/companies/...
 *
 * IMPORTANT: `config_json` MUST be an object, not a JSON-serialized string.
 * The backend (CompanyInSchema) validates with Pydantic and rejects strings:
 *   ValueError("config_json debe ser un objeto JSON (dict)")
 */
export interface EmpresaPayload {
  name?: string;
  initial_template?: string;
  tax_id?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  cp?: string;
  country?: string;
  country_code?: string;
  website?: string;
  config_json: Record<string, unknown>;
  default_language?: string;
  timezone?: string;
  currency?: string;
}

export type BillingCycle = 'monthly' | 'yearly'

export interface BillingSubscriptionResult {
  mode?: string
  plan?: string
  billing_cycle?: BillingCycle
  subscription_id?: string
  checkout_url?: string
  trial_ends_at?: string
}

export interface CrearEmpresaResponse {
  msg: string
  id?: string | number
  subscription?: BillingSubscriptionResult | null
  subscriptionError?: string | null
}
