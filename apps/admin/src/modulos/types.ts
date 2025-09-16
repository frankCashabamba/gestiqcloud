export interface Modulo {
  id: number;
  nombre: string;
  slug: string;
  icono?: string;
  descripcion?: string;
  url?: string;
  plantilla_inicial: string;
  context_type?: string;
  modelo_objetivo?: string;
  filtros_contexto?: Record<string, any>;
  activo: boolean;
  categoria?: string;
}
export interface EmpresaModulo {
  id: number;
  empresa_id: number;
  modulo_id: number;
  fecha_activacion: string;
  fecha_expiracion?: string | null;
  activo: boolean;
  modulo: Modulo;         // ✅ <- Esto soluciona el error 'modulo' no existe
  empresa_slug: string;  // ✅ <- Solo si decides enviarlo desde el backend
}


export interface ModuloComun {
  id: number;
  empresa_id: number;
  empresa_slug: string;
  modulo_id: number;
  modulo: {
    id: number;
    nombre: string;
    url?: string;    // ← ahora es string | undefined
    icono?: string;  // ← también opcional
  };
}

export interface ModuloAsignado {
  id: number;
  empresa_id: number;
  empresa_slug: string;
  modulo_id: number;
  fecha_activacion: string;
  fecha_expiracion: string | null;
  modulo: {
    id: number;
    nombre: string;
    url: string;
    icono?: string;
  };
}
