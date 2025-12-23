export interface Empresa {
  id: number;
  nombre: string;
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
  color_primario: string;
  plantilla_inicio: string;
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

export interface CrearEmpresaResponse {
  msg: string;
  id?: number;
}
