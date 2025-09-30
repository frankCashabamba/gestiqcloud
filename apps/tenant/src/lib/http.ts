// lib/http.ts
import { env } from '../env'

export const API_URL = (env.apiUrl || '/api').replace(/\/+$/g, '')

export type HttpOptions = RequestInit & { authToken?: string; retryOn401?: boolean };

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

const EXEMPT_CSRF_SUFFIX = ['/auth/login', '/auth/refresh', '/auth/logout'];

function needsCsrf(path: string, method: string) {
  const isSafe = ['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase());
  if (isSafe) return false;
  return !EXEMPT_CSRF_SUFFIX.some((s) => path.endsWith(s));
}

// 🔧 Normaliza URL para evitar /api/api/... y // duplicadas
function buildUrl(base: string, path: string) {
  const b = (base || '').replace(/\/+$/g, '')
  let p = path || ''
  p = p.startsWith('/') ? p : `/${p}`

  let basePathname = b
  try {
    basePathname = new URL(b, window.location.origin).pathname.replace(/\/+$/g, '')
  } catch {
    /* base relativa */
  }
  const baseHasApi = /^\/api(\/|$)/.test(basePathname)
  if (baseHasApi) p = p.replace(/^\/api(\/|$)/, '/')

  const joined = (b + p).replace(/([^:])\/{2,}/g, '$1/')
  return joined
}

async function safeJson(res: Response) {
  const txt = await res.text();
  try { return txt ? JSON.parse(txt) : null; } catch { return null; }
}

export async function apiFetch<T = unknown>(
  path: string,
  { authToken, retryOn401 = true, headers, credentials, ...init }: HttpOptions = {}
): Promise<T> {
  const url = buildUrl(API_URL, path);
  const method = (init.method ?? 'GET').toUpperCase();

  const h = new Headers(headers || {});
  if (!h.has('Content-Type')) h.set('Content-Type', 'application/json');
  if (authToken) h.set('Authorization', `Bearer ${authToken}`);

  // CSRF: soporta varios nombres de cookie habituales
  if (needsCsrf(path, method)) {
    const csrf =
      getCookie('csrf_token') ||
      getCookie('csrftoken') ||
      getCookie('XSRF-TOKEN');
    if (csrf && !h.has('X-CSRFToken') && !h.has('X-CSRF-Token') && !h.has('X-XSRF-TOKEN')) {
      h.set('X-CSRFToken', csrf); // cambia a la cabecera que tu backend espere si es otra
    }
  }

  const res = await fetch(url, { credentials: credentials ?? 'include', headers: h, ...init });

  if (res.status === 401 && retryOn401) {
    throw Object.assign(new Error('Unauthorized'), { status: 401 });
  }
  if (!res.ok) {
    const retryAfter = res.headers.get('Retry-After');
    const detail = await safeJson(res);
    const error = new Error((detail as any)?.detail || res.statusText) as Error & { status?: number; retryAfter?: string | null };
    error.status = res.status;
    error.retryAfter = retryAfter;
    throw error;
  }
  return (await safeJson(res)) as T;
}
