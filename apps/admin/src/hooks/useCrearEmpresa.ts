// src/hooks/useCrearEmpresa.ts
import { useState } from "react";
import type { FormularioEmpresa, CrearEmpresaResponse } from "../typesall/empresa";
import { crearEmpresaCompleta } from "../services/empresa";
import { buildEmpresaFormData } from "../utils/formToFormData";

export const useCrearEmpresa = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const crear = async (datos: FormularioEmpresa): Promise<CrearEmpresaResponse | null> => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const form = buildEmpresaFormData(datos);
      const res = await crearEmpresaCompleta(form);
      setSuccess(res.msg || "Empresa creada correctamente");
      return res;
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Error desconocido");
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    crear,
    loading,
    error,
    success,
  };
};
