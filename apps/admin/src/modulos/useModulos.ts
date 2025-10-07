import { useEffect, useState } from "react";
import api from "../utils/axios";

export interface Modulo {
  id: number;
  nombre: string;
  icono: string;
  descripcion?: string;
}

export type UseModulosResult = {
  modulos: Modulo[];
  loading: boolean;
  error: string | null;
};

export function useModulos(): UseModulosResult {
  const [modulos, setModulos] = useState<Modulo[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await api.get<Modulo[]>(
          "/v1/admin/modulos/publicos",
          { signal: ac.signal } as any
        );
        setModulos(res.data || []);
      } catch (err: any) {
        if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") return;
        console.error("Error cargando módulos", err);
        setError(err?.response?.data?.detail || err?.message || "No se pudieron cargar los módulos");
      } finally {
        setLoading(false);
      }
    })();
    return () => ac.abort();
  }, []);

  return { modulos, loading, error };
}
