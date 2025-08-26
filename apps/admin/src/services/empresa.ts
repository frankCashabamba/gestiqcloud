// src/services/empresa.ts

import type { Empresa } from "../typesall/empresa";
import { apiGet, apiPost, apiPut, apiDelete,apiPostForm } from "../lib/api";
import type { CrearEmpresaResponse } from "../typesall/empresa";

const BASE = "/lista/empresas";

// GET: listar todas las empresas
export const getEmpresas = () => apiGet<Empresa[]>(BASE);

// POST: crear empresa
export const createEmpresa = (data: Partial<Empresa>) =>
  apiPost<Empresa>(BASE, data);

// PUT: actualizar empresa
export const updateEmpresa = (id: number, data: Partial<Empresa>) =>
  apiPut<Empresa>(`${BASE}/${id}`, data);

// DELETE: eliminar empresa
export const deleteEmpresa = (id: number) =>
  apiDelete<{ success: boolean }>(`${BASE}/${id}`);

export const crearEmpresaCompleta = (form: FormData) =>
  apiPostForm<CrearEmpresaResponse>("/empresas/completa", form);
