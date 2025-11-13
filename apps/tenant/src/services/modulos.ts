import { apiFetch } from "../lib/http";

export type Modulo = { id: number; name: string; url?: string; slug?: string; icono?: string; categoria?: string; active: boolean };

// Tenant endpoint exposes GET /api/v1/modulos/ (lista asignada)
export const listMisModulos = (authToken?: string) => apiFetch<Modulo[]>("/api/v1/modulos/", { authToken });
export const listModulosSeleccionablesPorEmpresa = (empresaSlug: string) =>
  apiFetch<Modulo[]>(`/api/v1/modulos/empresa/${encodeURIComponent(empresaSlug)}/seleccionables`);
