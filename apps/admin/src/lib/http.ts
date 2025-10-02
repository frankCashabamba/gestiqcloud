// lib/http.ts
// Deprecated: this local HTTP helper has been superseded by @shared client.
import { env } from '../env'

export const API_URL = (env.apiUrl || '/api').replace(/\/+$/g, '')

export type HttpOptions = RequestInit & { authToken?: string; retryOn401?: boolean };

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

const EXEMPT_CSRF_SUFFIX = [
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
  '/admin/auth/login',   // 👈 añade admin
  '/admin/auth/refresh', // 👈 añade admin
  '/admin/auth/logout',  // 👈 añade admin
  '/admin/auth/csrf',    // 👈 si usas el bootstrap CSRF
];
const NO_AUTH_HEADER_SUFFIX = [
  '/auth/login', '/auth/refresh', '/auth/logout',
  '/admin/auth/login', '/admin/auth/refresh', '/admin/auth/logout', '/admin/auth/csrf',
];

function needsCsrf(path: string, method: string) {
  const isSafe = ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
  if (isSafe) return false;
  return !EXEMPT_CSRF_SUFFIX.some((s) => path.endsWith(s));
}


// 🔧 Normaliza URL (sin romper http://) y evita /api/api
function buildUrl(base: string, path: string) {
  const b = (base || "").replace(/\/+$/g, "");
  let p = path || "";
  p = p.startsWith("/") ? p : `/${p}`;

  // Detecta si la BASE tiene /api en el pathname (soporta absolutas o relativas)
  let basePathname = b;
  try {
    basePathname = new URL(b, window.location.origin).pathname.replace(/\/+$/g, "");
  } catch {
    /* base relativa, usamos tal cual */
  }
  const baseHasApi = /^\/api(\/|$)/.test(basePathname);

  // Si base ya trae /api, quitar /api inicial del path
  if (baseHasApi) p = p.replace(/^\/api(\/|$)/, "/");

  // Une sin colapsar el protocolo
  const joined = (b + p).replace(/([^:])\/{2,}/g, "$1/");
  return joined;
}

async function safeJson(res: Response) {
  const txt = await res.text();
  try {
    return txt ? JSON.parse(txt) : null;
  } catch {
    return null;
  }
}

/** ====== Handlers registrables desde AuthProvider ====== */
type GetToken = () => string | null;
type SetToken = (t: string | null) => void;
type RefreshFn = () => Promise<string | null>;

let getTokenHandler: GetToken | null = null;
let setTokenHandler: SetToken | null = null;
let refreshHandler: RefreshFn | null = null;

export function registerAuthHandlers(h: { getToken?: GetToken; setToken?: SetToken; refresh?: RefreshFn }) {
  if (h.getToken) getTokenHandler = h.getToken;
  if (h.setToken) setTokenHandler = h.setToken;
  if (h.refresh) refreshHandler = h.refresh;
}

/** Error tipado */
export class HttpError extends Error {
  status?: number;
  retryAfter?: string | null;
  data?: any;
}

/** Evita múltiples refresh concurrentes */
let inflightRefresh: Promise<string | null> | null = null;

export async function apiFetch<T = unknown>(
  path: string,
  { authToken, retryOn401 = true, headers, credentials, ...init }: HttpOptions = {}
): Promise<T> {
  const url = buildUrl(API_URL, path);
  const method = (init.method ?? "GET").toUpperCase();

  const h = new Headers(headers || {});

  // Accept siempre; Content-Type sólo si no es GET y no estás mandando FormData
  if (!h.has("Accept")) h.set("Accept", "application/json");
  const isFormData = typeof FormData !== "undefined" && (init as any)?.body instanceof FormData;
  if (method !== "GET" && !isFormData && !h.has("Content-Type")) h.set("Content-Type", "application/json");

  // Usa el token explícito o el global
  const skipAuthHeader = NO_AUTH_HEADER_SUFFIX.some((s) => path.endsWith(s));
  const tokenToUse = skipAuthHeader
  ? null
  : authToken ?? (getTokenHandler ? getTokenHandler() : null);

if (tokenToUse && !h.has('Authorization')) {
  h.set('Authorization', `Bearer ${tokenToUse}`);
}

  // CSRF (para métodos no seguros, excepto exentos)
  if (needsCsrf(path, method)) {
    const csrf = getCookie("csrf_token") || getCookie("csrftoken") || getCookie("XSRF-TOKEN");
    if (csrf && !h.has("X-CSRFToken") && !h.has("X-CSRF-Token") && !h.has("X-XSRF-TOKEN")) {
      h.set("X-CSRFToken", csrf); // ajusta al header que tu backend espere
    }
  }

  async function doFetch() {
    return fetch(url, { credentials: credentials ?? "include", headers: h, ...init });
  }

  let res = await doFetch();

  // ⏪ 401 -> intenta refresh (una sola vez y de forma compartida) y reintenta
if (res.status === 401 && retryOn401 && refreshHandler) {
  try {
    inflightRefresh = inflightRefresh || refreshHandler();
    const newTok = await inflightRefresh;
    if (newTok) {
      if (setTokenHandler) setTokenHandler(newTok);
      h.set("Authorization", `Bearer ${newTok}`);
      res = await doFetch();
    }
  } catch {
    // silencioso: 401 se gestionará abajo
  } finally {
    inflightRefresh = null; // ✅ siempre se limpia
  }
}

  if (res.status === 401) {
    const err = new HttpError("Unauthorized");
    err.status = 401;
    throw err;
  }

  if (!res.ok) {
    const retryAfter = res.headers.get("Retry-After");
    const detail = await safeJson(res);
    const error = new HttpError((detail as any)?.detail || res.statusText);
    error.status = res.status;
    error.retryAfter = retryAfter;
    error.data = detail;
    throw error;
  }

  return (await safeJson(res)) as T;
}
