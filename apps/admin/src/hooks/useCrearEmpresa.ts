// src/hooks/useCrearEmpresa.ts
import { useState } from "react";
import type { FormularioEmpresa, CrearEmpresaResponse } from "../typesall/empresa";
import { createEmpresaFull } from "../services/empresa";
import { buildEmpresaCompletaPayload } from "../utils/formToJson";
import { getErrorMessage } from "../shared/toast";

export const useCrearEmpresa = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const crear = async (datos: FormularioEmpresa): Promise<CrearEmpresaResponse | null> => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setFieldErrors({});

    try {
      const payload = await buildEmpresaCompletaPayload(datos);
      const res = await createEmpresaFull(payload);
      setSuccess("Empresa creada con admin, módulos y logo");
      return res;
    } catch (err: any) {
      // Mensajes afinados según 'detail' del backend
      const detail = err?.response?.data?.detail || err?.data?.detail || err?.detail;
      if (detail === 'empresa_ruc_exists') {
        setError('El RUC ya está registrado. Verifica los datos.');
        setFieldErrors({ ruc: 'RUC ya registrado' });
      } else if (detail === 'user_email_or_username_taken') {
        setError('El correo o el usuario ya existen. Prueba con otros.');
        setFieldErrors({ email: 'Correo ya existente', username: 'Usuario ya existente' });
      } else {
        const msg = getErrorMessage(err);
        setError(msg);
      }
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
    fieldErrors,
  };
};

