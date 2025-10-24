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
  const [needSecondSurname, setNeedSecondSurname] = useState(false);

  const crear = async (datos: FormularioEmpresa): Promise<CrearEmpresaResponse | null> => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setFieldErrors({});
    setNeedSecondSurname(false);

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
        // Intento automático solo para username si tenemos segundo apellido
        const base = (datos.username || '').trim();
        const segundo = (datos.segundo_apellido_encargado || '').trim().toLowerCase().replace(/\s+/g, '');
        if (!segundo) {
          setNeedSecondSurname(true);
          setError('El usuario ya existe. Ingresa segundo apellido para sugerir uno único.');
          setFieldErrors({ username: 'Usuario ya existente' });
          return null;
        }
        // Probar agregando letras progresivamente del segundo apellido
        for (let k = 1; k <= Math.min(segundo.length, 20); k++) {
          const candidate = `${base}${segundo.slice(0, k)}`;
          try {
            const payload2 = await buildEmpresaCompletaPayload({ ...datos, username: candidate });
            const res2 = await createEmpresaFull(payload2);
            setSuccess("Empresa creada con admin, módulos y logo");
            return res2;
          } catch (e: any) {
            const d2 = e?.response?.data?.detail || e?.data?.detail || e?.detail;
            if (d2 !== 'user_email_or_username_taken') {
              const msg = (e && (e.message || d2)) || 'Error inesperado';
              setError(msg);
              return null;
            }
            // else: seguir intentando siguiente letra
          }
        }
        // Último recurso: sufijos numéricos
        for (let n = 1; n <= 99; n++) {
          const candidate = `${base}${segundo[0] || ''}${n}`;
          try {
            const payload3 = await buildEmpresaCompletaPayload({ ...datos, username: candidate });
            const res3 = await createEmpresaFull(payload3);
            setSuccess("Empresa creada con admin, módulos y logo");
            return res3;
          } catch (e: any) {
            const d3 = e?.response?.data?.detail || e?.data?.detail || e?.detail;
            if (d3 !== 'user_email_or_username_taken') {
              const msg = (e && (e.message || d3)) || 'Error inesperado';
              setError(msg);
              return null;
            }
          }
        }
        setError('No se pudo generar un usuario único automáticamente. Inténtalo nuevamente.');
        setFieldErrors({ username: 'No disponible' });
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
    needSecondSurname,
  };
};
