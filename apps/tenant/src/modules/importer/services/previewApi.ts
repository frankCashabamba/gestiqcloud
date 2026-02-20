/**
 * API de Vista Previa de Importación
 */

import { apiFetch } from '../../../lib/http';
import { IMPORTS } from '@endpoints/imports'

const API_BASE = IMPORTS.public.preview;

export interface PreviewResponse {
  success: boolean;
  analysis: {
    headers: string[];
    header_row: number;
    total_rows: number;
    total_columns: number;
    suggested_mapping: Record<string, string>;
  };
  preview_items: Array<{
    nombre: string;
    precio: number;
    cantidad: number;
    categoria: string;
    _validation?: {
      valid: boolean;
      errors: string[];
    };
    _normalized?: Record<string, any>;
  }>;
  categories: string[];
  stats: {
    total: number;
    categories: number;
    with_stock?: number;
    zero_stock?: number;
  };
  suggestions: Record<string, string>;
}

/**
 * Analiza un archivo Excel y devuelve vista previa
 */
export async function analyzeExcelForPreview(file: File): Promise<PreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return apiFetch<PreviewResponse>(`${API_BASE}/analyze-excel`, {
    method: 'POST',
    body: formData,
  });
}

/**
 * Valida un mapeo de columnas contra una fila de muestra
 */
export async function validateMapping(
  mapping: Record<string, string>,
  sampleRow: Record<string, any>
) {
  return apiFetch(`${API_BASE}/validate-mapping`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mapping, sample_row: sampleRow }),
  });
}

/**
 * Lista templates de importación guardados
 */
export async function listImportTemplates() {
  return apiFetch(`${API_BASE}/templates`);
}

/**
 * Guarda un template de mapeo
 */
export async function saveImportTemplate(
  name: string,
  sourceType: string,
  mappings: Record<string, string>
) {
  return apiFetch(`${API_BASE}/save-template`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, source_type: sourceType, mappings }),
  });
}
