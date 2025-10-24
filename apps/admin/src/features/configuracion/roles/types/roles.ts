// src/pages/configuracion/roles/types/roles.ts

export interface RoleFromBackend {
  id: number;
  nombre: string;
  descripcion: string;
  permisos: string[]; // Array de strings desde backend
}

export interface Role {
  id: number;
  nombre: string;
  descripcion: string;
  permisos: Record<string, boolean>; // Objeto para frontend
}

export interface RoleData {
  id?: number;
  nombre: string;
  descripcion: string;
  permisos: string[]; // Para enviar al backend
}
