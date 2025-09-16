// src/hooks/useEmpresas.ts
import { useEffect, useState } from "react";
import type { Empresa } from "../typesall/empresa";
import { getEmpresas } from "../services/empresa";

export const useEmpresas = () => {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await getEmpresas();
        if (!alive) return;
        setEmpresas(Array.isArray(data) ? data : []);
        setError(null);
      } catch (e: any) {
        if (!alive) return;
        console.error("getEmpresas error:", e);
        setError(e?.message || "Error al cargar empresas");
        setEmpresas([]); // sólo para estado consistente
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  return { empresas, loading, error };
}
