import api from '../shared/api/client';

export interface CompanySettings {
  locale?: string;
  timezone?: string;
  currency?: string;
  country?: string;
  sector_id?: number | string | null;
  sector_plantilla_name?: string | null;
  sector_template_name?: string | null;
  sector_plantilla_nombre?: string | null; // alias para escribir/leer
  pos?: {
    receipt_width_mm?: number;
    tax_price_includes?: boolean;
    default_tax_rate?: number;
    return_window_days?: number;
    store_credit?: {
      enabled?: boolean;
      single_use?: boolean;
      expiry_months?: number;
    };
  };
  inventory?: {
    track_lots?: boolean;
    track_expiry?: boolean;
    allow_negative_stock?: boolean;
    reorder_point_default?: number;
  };
  invoicing?: {
    auto_numbering?: boolean;
    series_prefix?: string;
    starting_number?: number;
    reset_yearly?: boolean;
    include_logo?: boolean;
    footer_text?: string;
  };
  einvoicing?: {
    sri?: {
      enabled?: boolean;
      environment?: 'staging' | 'production';
      certificate_path?: string;
      auto_send?: boolean;
    };
    sii?: {
      enabled?: boolean;
      agency?: string;
      certificate_path?: string;
      auto_send?: boolean;
    };
  };
  purchases?: any;
  expenses?: any;
  finance?: any;
  hr?: any;
  sales?: any;
}

export type CompanyLimits = {
  user_limit?: number;
  allow_custom_roles?: boolean;
};

export async function getCompanySettings(tenantId: string): Promise<CompanySettings> {
  const response = await api.get(`/v1/admin/companies/${tenantId}/company/settings`);
  return response.data;
}

export async function updateCompanySettings(tenantId: string, settings: Partial<CompanySettings>) {
  const response = await api.put(`/v1/admin/companies/${tenantId}/company/settings`, settings);
  return response.data;
}

export async function getCompanyLimits(tenantId: string): Promise<CompanyLimits> {
  const response = await api.get(`/v1/admin/companies/${tenantId}/company/settings/limits`);
  return response.data;
}

export async function updateCompanyLimits(tenantId: string, limits: CompanyLimits) {
  const response = await api.put(`/v1/admin/companies/${tenantId}/company/settings/limits`, limits);
  return response.data;
}

export async function updateModuleSettings(
  tenantId: string,
  module: string,
  config: any
) {
  const response = await api.put(
    `/v1/admin/companies/${tenantId}/settings/${module}`,
    config
  );
  return response.data;
}

export async function uploadCertificate(
  tenantId: string,
  type: 'sri' | 'sii',
  file: File,
  password: string
) {
  const formData = new FormData();
  formData.append('certificate', file);
  formData.append('password', password);

  const response = await api.post(
    `/v1/admin/companies/${tenantId}/einvoicing/${type}/certificate`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
}

export async function exportSettings(tenantId: string): Promise<Blob> {
  const response = await api.get(`/v1/admin/companies/${tenantId}/settings/export`, {
    responseType: 'blob',
  });
  return response.data;
}

export async function restoreDefaults(tenantId: string) {
  const response = await api.post(`/v1/admin/companies/${tenantId}/settings/restore-defaults`);
  return response.data;
}

export const TIMEZONES = [
  'America/Guayaquil',
  'America/New_York',
  'America/Los_Angeles',
  'America/Mexico_City',
  'Europe/Madrid',
  'Europe/London',
  'Europe/Paris',
  'UTC',
];

export const CURRENCIES = [
  { code: 'EUR', name: 'Euro' },
  { code: 'USD', name: 'US Dollar' },
  { code: 'GBP', name: 'British Pound' },
  { code: 'MXN', name: 'Mexican Peso' },
];

export const COUNTRIES = [
  { code: 'ES', name: 'España' },
  { code: 'EC', name: 'Ecuador' },
  { code: 'MX', name: 'México' },
  { code: 'US', name: 'Estados Unidos' },
];
