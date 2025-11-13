/**
 * Hook para manejar el flujo completo de vista previa
 */
import { useState } from 'react';
import { analyzeExcelForPreview, type PreviewResponse } from '../services/previewApi';

export function useImportPreview() {
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeFile = async (file: File) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await analyzeExcelForPreview(file);
      setPreview(result);
      return result;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const clearPreview = () => {
    setPreview(null);
    setError(null);
  };

  return {
    preview,
    loading,
    error,
    analyzeFile,
    clearPreview,
  };
}
