/* Edge Gateway (Cloudflare Worker)
 * - Restrictive CORS with credentials
 * - Host allow-list and path allow-list (optional)
 * - Request ID propagation (X-Request-Id)
 * - Secure headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
 * - Cookie rewriting for access_token (Lax) and refresh_token (None)
 *
 * Env (Bindings):
 * - UPSTREAM_BASE: Origin base URL of the backend (e.g., https://gestiqcloud-api.onrender.com)
 * - ALLOWED_ORIGINS: Comma-separated list of allowed origins for CORS (e.g., https://gestiqcloud.com,https://admin.gestiqcloud.com)
 * - COOKIE_DOMAIN: Cookie domain to enforce (e.g., .gestiqcloud.com)
 * - HSTS_ENABLED: "1" to enable HSTS
 */

/* Edge Gateway (Cloudflare Worker) — robust login cookies & CORS */

export default {
  async fetch(request, env, ctx) {
    const upstreamBase = (env.TARGET || env.UPSTREAM_BASE || '').replace(/\/+$/g, '');
    if (!upstreamBase) {
      return new Response('Gateway misconfigured: missing TARGET/UPSTREAM_BASE', { status: 500 });
    }

    const url = new URL(request.url);
    const reqHeaders = new Headers(request.headers);

    // Request ID
    const reqId = reqHeaders.get('X-Request-Id') || crypto.randomUUID();
    reqHeaders.set('X-Request-Id', reqId);

    // CORS
    const allowed = parseAllowedOrigins(env.ALLOWED_ORIGINS);
    const origin = reqHeaders.get('Origin') || '';
    const isPreflight = request.method === 'OPTIONS';

    // Bloquear orígenes no permitidos (con credenciales)
    if (origin && !isOriginAllowed(origin, allowed)) {
      if (isPreflight) {
        return preflightResponse(origin, allowed, request);
      }
      return withCors(
        new Response(JSON.stringify({ detail: 'origin_not_allowed' }), {
          status: 403,
          headers: { 'content-type': 'application/json' },
        }),
        origin,
        allowed
      );
    }

    // Preflight
    if (isPreflight) {
      return preflightResponse(origin, allowed, request);
    }

    // Allow-list por path y reescrituras según host
    const path = url.pathname;
    const host = url.hostname;

    // Soporte limpio en api.gestiqcloud.com: acepta /v1/* y /health sin prefijo /api
    let forwardPath = path;
    if (host === 'api.gestiqcloud.com') {
      if (path === '/') {
        const body = JSON.stringify({
          service: 'GestiqCloud API',
          version: env.API_VERSION || '1.0.0',
          docs: '/docs',
          health: '/health',
          api: '/api/v1',
        });
        return withCors(
          new Response(body, { status: 200, headers: { 'content-type': 'application/json' } }),
          origin,
          allowed
        );
      }
      if (path === '/health' || path === '/ready') {
        return withCors(new Response('ok', { status: 200 }), origin, allowed);
      }
      if (path.startsWith('/v1/')) {
        forwardPath = '/api' + path; // reescribe a upstream /api/v1/*
      } else if (!path.startsWith('/api/')) {
        return new Response('Not found', { status: 404 });
      }
    } else if (host === 'admin.gestiqcloud.com' || host === 'www.gestiqcloud.com') {
      // Acepta /v1/* para admin/www y reescribe a /api/v1/*
      if (path.startsWith('/v1/')) {
        forwardPath = '/api' + path;
      } else if (path.startsWith('/api/')) {
        forwardPath = path;
      } else {
        return new Response('Not found', { status: 404 });
      }
    } else {
      // Otros hosts: exigir prefijo /api/
      if (!path.startsWith('/api/')) {
        return new Response('Not found', { status: 404 });
      }
    }

    if (host === 'admin.gestiqcloud.com' && forwardPath.startsWith('/api/v1/tenant/')) {
      return new Response('Forbidden', { status: 403 });
    }
    if (host === 'www.gestiqcloud.com' && forwardPath.startsWith('/api/v1/admin/')) {
      return new Response('Forbidden', { status: 403 });
    }

    // Proxy a upstream (preserva path+query)
    const upstreamURL = upstreamBase + forwardPath + url.search;

    // Clonar request y ajustar hop-by-hop
    const init = {
      method: request.method,
      headers: new Headers(reqHeaders),
      // MUY IMPORTANTE: no sigas redirecciones para no perder Set-Cookie en 3xx
      redirect: 'manual',
    };
    if (!['GET', 'HEAD'].includes(request.method)) {
      // Pasa el cuerpo tal cual
      init.body = request.body;
    }
    // hop-by-hop
    init.headers.delete('host');
    init.headers.delete('content-length');
    init.headers.set('x-forwarded-host', url.hostname);
    init.headers.set('x-forwarded-proto', 'https');

    let upstreamResp;
    try {
      upstreamResp = await fetch(upstreamURL, init);
    } catch (e) {
      return withCors(
        new Response('Upstream unavailable', { status: 502 }),
        origin,
        allowed
      );
    }

    // Clonar headers de respuesta
    const respHdrs = new Headers(upstreamResp.headers);

    // Seguridad
    respHdrs.set('X-Request-Id', reqId);
    respHdrs.set('X-Frame-Options', 'DENY');
    respHdrs.set('X-Content-Type-Options', 'nosniff');
    respHdrs.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    if ((env.HSTS_ENABLED || '1') === '1' && url.protocol === 'https:') {
      respHdrs.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    }

    // CORS (respuesta real)
    applyCorsHeaders(respHdrs, origin, allowed);

    // Reescritura de cookies (robusta y forzando Path=/)
    rewriteCookiesRobust(upstreamResp.headers, respHdrs, env.COOKIE_DOMAIN || extractCookieDomain(url.host));

    // Importante: evita content-length incoherente (lo recalcula CF)
    respHdrs.delete('content-length');

    // Devuelve la respuesta tal cual (incluida 3xx si la hay) con sus headers reescritos
    return new Response(upstreamResp.body, {
      status: upstreamResp.status,
      statusText: upstreamResp.statusText,
      headers: respHdrs,
    });
  },
};

/* ===== Helpers ===== */

function parseAllowedOrigins(csv) {
  const defaults = [
    'https://gestiqcloud.com',
    'https://www.gestiqcloud.com',
    'https://admin.gestiqcloud.com',
  ];
  if (!csv) return defaults;
  const list = String(csv)
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  return list.length ? list : defaults;
}

function isOriginAllowed(origin, list) {
  try {
    const o = new URL(origin);
    return list.includes(o.origin);
  } catch {
    return false;
  }
}

function preflightResponse(origin, allowed, request) {
  const h = new Headers();
  if (origin && isOriginAllowed(origin, allowed)) {
    const acrh = request.headers.get('Access-Control-Request-Headers');
    h.set('Access-Control-Allow-Origin', origin);
    h.append('Vary', 'Origin');
    h.set('Access-Control-Allow-Credentials', 'true');
    h.set('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');
    // Reflejar lo pedido + tu lista por si acaso
    h.set(
      'Access-Control-Allow-Headers',
      acrh || 'Authorization,Content-Type,X-Client-Version,X-Client-Revision,X-CSRF-Token,X-CSRFToken'
    );
    h.set('Access-Control-Max-Age', '86400');
  }
  return new Response(null, { status: 204, headers: h });
}

function withCors(resp, origin, allowed) {
  const h = new Headers(resp.headers);
  if (origin && isOriginAllowed(origin, allowed)) {
    h.set('Access-Control-Allow-Origin', origin);
    // conservar otros Vary si existiesen
    const vary = h.get('Vary');
    h.set('Vary', vary ? `${vary}, Origin` : 'Origin');
    h.set('Access-Control-Allow-Credentials', 'true');
  }
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h });
}

function applyCorsHeaders(headers, origin, allowed) {
  if (origin && isOriginAllowed(origin, allowed)) {
    headers.set('Access-Control-Allow-Origin', origin);
    const vary = headers.get('Vary');
    headers.set('Vary', vary ? `${vary}, Origin` : 'Origin');
    headers.set('Access-Control-Allow-Credentials', 'true');
  } else {
    headers.delete('Access-Control-Allow-Origin');
    headers.delete('Access-Control-Allow-Credentials');
  }
}

function extractCookieDomain(host) {
  const parts = String(host).split('.');
  if (parts.length >= 2) return '.' + parts.slice(-2).join('.');
  return host;
}

function rewriteCookiesRobust(srcHeaders, dstHeaders, cookieDomain) {
  // Recoge todas las ocurrencias reales de Set-Cookie
  const cookies = [];
  srcHeaders.forEach((v, k) => {
    if (k.toLowerCase() === 'set-cookie') cookies.push(v);
  });
  if (!cookies.length) return;

  dstHeaders.delete('Set-Cookie');

  for (let c of cookies) {
    let v = c;

    // Normaliza Domain
    if (/;\s*Domain=/i.test(v)) {
      v = v.replace(/;\s*Domain=[^;]*/i, `; Domain=${cookieDomain}`);
    } else {
      v += `; Domain=${cookieDomain}`;
    }

    // **Forzar Path=/** (clave para que aplique en todas las rutas)
    if (/;\s*Path=/i.test(v)) {
      v = v.replace(/;\s*Path=[^;]*/i, '; Path=/');
    } else {
      v += '; Path=/';
    }

    // Asegurar Secure/HttpOnly
    if (!/;\s*Secure/i.test(v)) v += '; Secure';
    if (!/;\s*HttpOnly/i.test(v)) v += '; HttpOnly';

    // SameSite por nombre
    if (/^refresh_token=/i.test(v)) {
      v = v.replace(/;\s*SameSite=[^;]*/i, '');
      v += '; SameSite=None';
    } else if (/^access_token=/i.test(v)) {
      v = v.replace(/;\s*SameSite=[^;]*/i, '');
      v += '; SameSite=Lax';
    }
    // si hay otras cookies, no tocamos SameSite (o podrías fijar Lax por defecto)

    dstHeaders.append('Set-Cookie', v);
  }
}
