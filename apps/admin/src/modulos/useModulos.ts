import { useEffect, useState } from "react";

import api from "../utils/axios";

export interface Modulo {
  id: string;
  name: string;
  icon?: string;
  description?: string;
  category?: string | null;
}

type BackendModulo = {
  id: string;
  name?: string;
  description?: string | null;
  icon?: string | null;
  category?: string | null;
};

export type UseModulosResult = {
  modulos: Modulo[];
  loading: boolean;
  error: string | null;
};

// Map common Spanish module slugs to their English label so we can dedupe
const SPANISH_TO_ENGLISH: Record<string, string> = {
  ventas: "Sales",
  facturacion: "Billing",
  facturacion_electronica: "eInvoicing",
  compras: "Purchases",
  proveedores: "Suppliers",
  clientes: "Customers",
  inventario: "Inventory",
  gastos: "Expenses",
  finanzas: "Finances",
  contabilidad: "Accounting",
  rrhh: "HR",
  recursos_humanos: "HR",
  produccion: "Productions",
  produccion_fabrica: "Productions",
  reportes: "Reports",
  ajustes: "Settings",
  configuracion: "Settings",
  notificaciones: "Notifications",
  punto_de_venta: "POS",
  tienda: "POS",
  plantillas: "Templates",
  usuarios: "Users",
  webhooks: "Webhooks",
  crm: "CRM",
  productos: "Products",
  conciliacion: "Reconciliation",
  conciliaciones: "Reconciliation",
};

const slugify = (value: string): string =>
  (value || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

function normalizeNameToEnglish(name: string): {
  displayName: string;
  key: string;
  wasTranslated: boolean;
} {
  const slug = slugify(name);
  const mapped = SPANISH_TO_ENGLISH[slug];
  const displayName = mapped || name;
  const key = slugify(mapped || name);
  return { displayName, key, wasTranslated: Boolean(mapped) };
}

function normalizeModulo(raw: BackendModulo): Modulo {
  return {
    id: String(raw.id),
    name: (raw.name || "").trim(),
    icon: raw.icon || undefined,
    description: raw.description || undefined,
    category: raw.category ?? null,
  };
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
          "/v1/admin/modules/public",
          { signal: ac.signal } as any
        );
        const data = res.data || [];
        const dedup = new Map<string, { modulo: Modulo; wasTranslated: boolean }>();

        data.map(normalizeModulo).forEach((m) => {
          const { displayName, key, wasTranslated } = normalizeNameToEnglish(m.name);
          const candidate: Modulo = { ...m, name: displayName };
          const current = dedup.get(key);

          if (!current) {
            dedup.set(key, { modulo: candidate, wasTranslated });
            return;
          }

          // Prefer the version that already comes in English (wasTranslated === false)
          if (current.wasTranslated && !wasTranslated) {
            dedup.set(key, { modulo: candidate, wasTranslated });
          }
        });

        setModulos(Array.from(dedup.values()).map((item) => item.modulo));
      } catch (err: any) {
        if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") return;
        console.error("Error cargando módulos", err);
        setError(
          err?.response?.data?.detail || err?.message || "No se pudieron cargar los módulos"
        );
      } finally {
        setLoading(false);
      }
    })();
    return () => ac.abort();
  }, []);

  return { modulos, loading, error };
}
