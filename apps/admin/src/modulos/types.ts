export interface Module {
  id: string;
  name: string;
  description?: string | null;
  url?: string | null;
  icon?: string | null;
  category?: string | null;
  active: boolean;
  initial_template: string;
  context_type?: string | null;
  target_model?: string | null;
  context_filters?: Record<string, any> | null;
}

export interface CompanyModule {
  id: string;
  tenant_id: string;
  company_slug?: string | null;
  module_id: string;
  active: boolean;
  activation_date?: string | null;
  expiration_date?: string | null;
  initial_template?: string | null;
  module: Module;
}

export interface UserModule {
  id: string;
  tenant_id: string;
  company_slug: string;
  module_id: string;
  module: {
    id: string;
    name: string;
    url?: string | null;
    icon?: string | null;
  };
  activation_date: string;
  expiration_date: string | null;
}
