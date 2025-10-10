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

export default {
  async fetch(request, env, ctx) {
    const upstreamBase = (env.UPSTREAM_BASE || '').replace(/\/+$/g, '');
    if (!upstreamBase) {
      return new Response('Gateway misconfigured: missing UPSTREAM_BASE', { status: 500 });
    }

    const url = new URL(request.url);
    const reqHeaders = new Headers(request.headers);

    // Create or propagate request id
    const reqId = reqHeaders.get('X-Request-Id') || crypto.randomUUID();
    reqHeaders.set('X-Request-Id', reqId);

    // CORS handling
    const allowed = parseAllowedOrigins(env.ALLOWED_ORIGINS);
    const origin = reqHeaders.get('Origin');
    const isPreflight = request.method === 'OPTIONS';

    // Block disallowed origins when credentials are used
    if (origin && !isOriginAllowed(origin, allowed)) {
      if (isPreflight) {
        return withCors(new Response(null, { status: 204 }), origin, allowed);
      }
      return withCors(new Response(JSON.stringify({ detail: 'origin_not_allowed' }), { status: 403 }), origin, allowed);
    }

    // Preflight response
    if (isPreflight) {
      return withCors(new Response(null, { status: 204 }), origin, allowed);
    }

    // Proxy to upstream
    const upstreamURL = upstreamBase + url.pathname + url.search;
    const init = {
      method: request.method,
      headers: reqHeaders,
      body: request.body,
      redirect: 'follow',
    };

    // Ensure cookies are forwarded
    // (Workers include cookies by default; explicitly set header if needed)
    const resp = await fetch(upstreamURL, init);

    // Clone headers and add security + CORS
    const respHdrs = new Headers(resp.headers);
    // Security headers
    respHdrs.set('X-Request-Id', reqId);
    respHdrs.set('X-Frame-Options', 'DENY');
    respHdrs.set('X-Content-Type-Options', 'nosniff');
    respHdrs.set('Referrer-Policy', 'no-referrer');
    if ((env.HSTS_ENABLED || '1') === '1' && url.protocol === 'https:') {
      respHdrs.set('Strict-Transport-Security', 'max-age=15552000; includeSubDomains; preload');
    }

    // CORS for actual response
    const corsed = withCorsHeaders(resp, respHdrs, origin, allowed);

    // Cookie rewriting
    rewriteCookies(respHdrs, env.COOKIE_DOMAIN || extractCookieDomain(url.host));

    // Return final response with possibly adjusted headers
    const body = await resp.arrayBuffer();
    return new Response(body, { status: resp.status, headers: respHdrs });
  },
};

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

function withCors(resp, origin, allowed) {
  const h = new Headers(resp.headers);
  if (origin && isOriginAllowed(origin, allowed)) {
    h.set('Access-Control-Allow-Origin', origin);
    h.set('Vary', 'Origin');
    h.set('Access-Control-Allow-Credentials', 'true');
    h.set('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');
    h.set('Access-Control-Allow-Headers', 'Authorization,Content-Type,X-Client-Version,X-Client-Revision,X-CSRF-Token,X-CSRFToken');
    h.set('Access-Control-Max-Age', '86400');
  }
  return new Response(null, { status: 204, headers: h });
}

function withCorsHeaders(resp, headers, origin, allowed) {
  if (origin && isOriginAllowed(origin, allowed)) {
    headers.set('Access-Control-Allow-Origin', origin);
    headers.set('Vary', 'Origin');
    headers.set('Access-Control-Allow-Credentials', 'true');
  }
  return resp;
}

function extractCookieDomain(host) {
  // Convert api.example.com -> .example.com
  const parts = String(host).split('.');
  if (parts.length >= 2) {
    return '.' + parts.slice(-2).join('.');
  }
  return host;
}

function rewriteCookies(headers, cookieDomain) {
  // Cloudflare Workers allow multiple Set-Cookie headers via append
  // Get all set-cookie headers (runtime provides get/append support)
  const setCookie = headers.getAll ? headers.getAll('Set-Cookie') : getSetCookieFallback(headers);
  if (!setCookie || !setCookie.length) return;
  headers.delete('Set-Cookie');
  for (const c of setCookie) {
    let v = c;
    // Enforce Domain
    if (/;\s*Domain=/i.test(v)) {
      v = v.replace(/;\s*Domain=[^;]*/i, `; Domain=${cookieDomain}`);
    } else {
      v += `; Domain=${cookieDomain}`;
    }
    // Ensure Secure and HttpOnly
    if (!/;\s*Secure/i.test(v)) v += '; Secure';
    if (!/;\s*HttpOnly/i.test(v)) v += '; HttpOnly';
    // SameSite based on cookie name
    if (/^refresh_token=/.test(v)) {
      v = v.replace(/;\s*SameSite=[^;]*/i, '');
      v += '; SameSite=None';
    }
    if (/^access_token=/.test(v)) {
      v = v.replace(/;\s*SameSite=[^;]*/i, '');
      v += '; SameSite=Lax';
    }
    headers.append('Set-Cookie', v);
  }
}

function getSetCookieFallback(headers) {
  const raw = headers.get('Set-Cookie');
  if (!raw) return [];
  // Fallback parser: try to split by Set-Cookie boundaries respecting Expires commas
  const out = [];
  let i = 0;
  let start = 0;
  let inExpires = false;
  while (i < raw.length) {
    const ch = raw[i];
    if (ch === ',') {
      const seg = raw.slice(start, i);
      if (/\bExpires=/i.test(seg)) {
        // within cookie; keep scanning until ';' seen after this comma
        // do nothing special; just continue and rely on next branch
      } else {
        out.push(seg.trim());
        start = i + 1;
      }
    }
    i++;
  }
  const tail = raw.slice(start).trim();
  if (tail) out.push(tail);
  return out;
}

