export interface Empresa {
  id: number;
  nombre: string;
  modulos?: string[];
}



export interface FormularioEmpresa {
  nombre_empresa: string;
  tipo_empresa: string;
  tipo_negocio: string;
  ruc: string;
  telefono: string;
  direccion: string;
  pais: string;
  provincia: string;
  ciudad: string;
  cp: string;
  sitio_web: string;
  logo: File | null;
  color_primario: string;
  plantilla_inicio: string;
  config_json: string;
  nombre_encargado: string;
  apellido_encargado: string;
  email: string;
  username: string;
  password?: string;
  modulos: number[];
}

export interface CrearEmpresaResponse {
  msg: string;
  id?: number;
}
