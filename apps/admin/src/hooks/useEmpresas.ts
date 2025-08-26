// src/hooks/useEmpresas.ts
import { useEffect, useState } from "react";
import type { Empresa } from "../typesall/empresa";
import { getEmpresas } from "../services/empresa";

export const useEmpresas = () => {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);
    getEmpresas()
      .then((data) => {
        setEmpresas(data);
        setError(null);
      })
      .catch((err) => {
        setError(err);
        console.error("❌ Error al cargar empresas:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  return { empresas, loading, error };
};
