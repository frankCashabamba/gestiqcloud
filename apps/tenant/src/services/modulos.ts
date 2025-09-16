import { apiFetch } from "../lib/http";

export type Modulo = { id: number; nombre: string; url?: string; slug?: string; icono?: string; categoria?: string; activo: boolean };

// Tenant endpoint exposes GET /api/v1/modulos/ (lista asignada)
export const listMisModulos = (authToken?: string) => apiFetch<Modulo[]>("/v1/modulos/", { authToken });
export const listModulosSeleccionablesPorEmpresa = (empresaSlug: string) =>
  apiFetch<Modulo[]>(`/v1/modulos/empresa/${encodeURIComponent(empresaSlug)}/seleccionables`);
