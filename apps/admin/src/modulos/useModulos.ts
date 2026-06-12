import { useEffect, useState } from "react";
import type { AxiosRequestConfig } from "axios";

import api from "../utils/axios";

export interface Modulo {
  id: string;
  name: string;
  url?: string | null;
  icon?: string;
  description?: string;
  category?: string | null;
}

type BackendModulo = {
  id: string;
  name?: string;
  url?: string | null;
  description?: string | null;
  icon?: string | null;
  category?: string | null;
};

export type UseModulosResult = {
  modulos: Modulo[];
  loading: boolean;
  error: string | null;
};

function slugify(value: string): string {
  return (value || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function normalizeModuloLookupKey(value: string): string {
  return slugify(value);
}

function prettifyModuloName(value: string): string {
  const raw = (value || "").trim();
  if (!raw) return "";
  if (/[A-Z]/.test(raw) || raw.includes(" ")) return raw;
  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeModulo(raw: BackendModulo): Modulo {
  return {
    id: String(raw.id),
    name: prettifyModuloName((raw.name || "").trim()),
    url: raw.url ?? null,
    icon: raw.icon || undefined,
    description: raw.description || undefined,
    category: raw.category ?? null,
  };
}

export function buildModuloLookup(modulos: Modulo[]): Map<string, string> {
  const lookup = new Map<string, string>();
  modulos.forEach((modulo) => {
    const keys = new Set<string>([
      normalizeModuloLookupKey(modulo.url || ""),
      normalizeModuloLookupKey(modulo.name),
      normalizeModuloLookupKey(modulo.id),
    ]);
    keys.forEach((key) => {
      if (key) lookup.set(key, modulo.id);
    });
  });
  return lookup;
}

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
        const res = await api.get<BackendModulo[]>(
          "/api/v1/admin/modules/public",
          { signal: ac.signal } as AxiosRequestConfig
        );
        const data = res.data || [];
        const dedup = new Map<string, Modulo>();

        data.map(normalizeModulo).forEach((modulo) => {
          const key =
            normalizeModuloLookupKey(modulo.url || "") ||
            normalizeModuloLookupKey(modulo.name) ||
            normalizeModuloLookupKey(modulo.id);
          if (!key) return;
          if (!dedup.has(key)) dedup.set(key, modulo);
        });

        setModulos(Array.from(dedup.values()));
      } catch (err: any) {
        if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") return;
        console.error("Error cargando mÃ³dulos", err);
        setError(
          err?.response?.data?.detail || err?.message || "No se pudieron cargar los mÃ³dulos"
        );
      } finally {
        setLoading(false);
      }
    })();
    return () => ac.abort();
  }, []);

  return { modulos, loading, error };
}
