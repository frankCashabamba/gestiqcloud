/* Edge Gateway (Cloudflare Worker)
 * - Restrictive CORS with credentials
 * - Host allow-list and path allow-list (optional)
 * - Request ID propagation (X-Request-Id)
 * - Secure headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
 * - Cookie rewriting for access_token (Lax) and refresh_token (None)
 *
 * Env (Bindings):
 * - TARGET / UPSTREAM_BASE: Origin base URL of the backend (e.g., https://gestiqcloud-api.onrender.com)
 * - ALLOWED_ORIGINS: Comma-separated list of allowed origins for CORS (e.g., https://gestiqcloud.com,https://admin.gestiqcloud.com)
 * - COOKIE_DOMAIN: Cookie domain to enforce (e.g., .gestiqcloud.com)
 * - HSTS_ENABLED: "1" to enable HSTS
 */

export default {
  async fetch(request, env, ctx) {
    // Validate TARGET (required - no hardcoded defaults)
    const upstreamBase = (env.TARGET || env.UPSTREAM_BASE || '').replace(/\/+$/g, '')
    if (!upstreamBase) {
      return new Response('Gateway misconfigured: missing TARGET/UPSTREAM_BASE', { status: 500 })
    }

    const url = new URL(request.url)
    const reqHeaders = new Headers(request.headers)

    // Request ID
    const reqId = reqHeaders.get('X-Request-Id') || crypto.randomUUID()
    reqHeaders.set('X-Request-Id', reqId)

    // CORS
    const allowed = parseAllowedOrigins(env.ALLOWED_ORIGINS)
    const origin = reqHeaders.get('Origin') || ''
    const isPreflight = request.method === 'OPTIONS'

    if (origin && !isOriginAllowed(origin, allowed)) {
      if (isPreflight) return preflightResponse(origin, allowed, request)
      return withCors(
        new Response(JSON.stringify({ detail: 'origin_not_allowed' }), {
          status: 403,
          headers: { 'content-type': 'application/json' },
        }),
        origin,
        allowed,
      )
    }
    if (isPreflight) return preflightResponse(origin, allowed, request)

    // Path routing
    const path = url.pathname
    const host = url.hostname
    let forwardPath = path

    if (host === 'api.gestiqcloud.com') {
      if (path === '/') {
        const body = JSON.stringify({
          service: 'GestiqCloud API',
          version: env.API_VERSION || '1.0.0',
          docs: '/docs',
          health: '/health',
          api: '/api/v1',
        })
        return withCors(new Response(body, { status: 200, headers: { 'content-type': 'application/json' } }), origin, allowed)
      }
      if (path === '/health' || path === '/ready') {
        return withCors(new Response('ok', { status: 200 }), origin, allowed)
      }
      if (path.startsWith('/api/')) {
        forwardPath = path // allow /api/v1/*
      } else if (path.startsWith('/v1/')) {
        forwardPath = '/api' + path // keep compatibility /v1 -> /api/v1
      } else {
        return withCors(new Response('Not found', { status: 404 }), origin, allowed)
      }
    } else if (host === 'admin.gestiqcloud.com' || host === 'www.gestiqcloud.com') {
      // allow both /v1/* and /api/v1/* for admin/www routes
      if (path.startsWith('/api/')) {
        forwardPath = path
      } else if (path.startsWith('/v1/')) {
        forwardPath = '/api' + path
      } else if (path === '/health' || path === '/ready') {
        return withCors(new Response('ok', { status: 200 }), origin, allowed)
      } else {
        return withCors(new Response('Not found', { status: 404 }), origin, allowed)
      }
    } else {
      // other hosts: allow /api/v1/* and /v1/*
      if (path.startsWith('/api/')) {
        forwardPath = path
      } else if (path.startsWith('/v1/')) {
        forwardPath = '/api' + path
      } else if (path === '/health' || path === '/ready') {
        return withCors(new Response('ok', { status: 200 }), origin, allowed)
      } else {
        return withCors(new Response('Not found', { status: 404 }), origin, allowed)
      }
    }

    // host-specific allow/deny after path normalization
    if (host === 'admin.gestiqcloud.com' && forwardPath.startsWith('/api/v1/tenant/')) {
      return withCors(new Response('Forbidden', { status: 403 }), origin, allowed)
    }
    if (host === 'www.gestiqcloud.com' && forwardPath.startsWith('/api/v1/admin/')) {
      return withCors(new Response('Forbidden', { status: 403 }), origin, allowed)
    }

    const upstreamURL = upstreamBase + forwardPath + url.search
    const init = {
      method: request.method,
      headers: new Headers(reqHeaders),
      redirect: 'manual', // don't follow redirects to preserve Set-Cookie
    }
    if (!['GET', 'HEAD'].includes(request.method)) {
      init.body = request.body
    }
    init.headers.delete('host')
    init.headers.delete('content-length')
    init.headers.set('x-forwarded-host', url.hostname)
    init.headers.set('x-forwarded-proto', 'https')

    let upstreamResp
    try {
      upstreamResp = await fetch(upstreamURL, init)
    } catch (e) {
      return withCors(new Response('Upstream unavailable', { status: 502 }), origin, allowed)
    }

    // clone response headers
    const respHdrs = new Headers(upstreamResp.headers)
    respHdrs.set('X-Request-Id', reqId)
    respHdrs.set('X-Frame-Options', 'DENY')
    respHdrs.set('X-Content-Type-Options', 'nosniff')
    respHdrs.set('Referrer-Policy', 'strict-origin-when-cross-origin')
    if ((env.HSTS_ENABLED || '1') === '1' && url.protocol === 'https:') {
      respHdrs.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload')
    }

    applyCorsHeaders(respHdrs, origin, allowed)
    rewriteCookiesRobust(upstreamResp.headers, respHdrs, env.COOKIE_DOMAIN || extractCookieDomain(url.host))
    respHdrs.delete('content-length')

    return new Response(upstreamResp.body, {
      status: upstreamResp.status,
      statusText: upstreamResp.statusText,
      headers: respHdrs,
    })
  },
}

/* ===== Helpers ===== */

function parseAllowedOrigins(csv) {
  if (!csv) {
    console.error('CRITICAL: ALLOWED_ORIGINS env var not configured')
    return []
  }
  const list = String(csv)
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  if (!list.length) {
    console.error('CRITICAL: ALLOWED_ORIGINS is empty after parsing')
    return []
  }
  return list
}

function isOriginAllowed(origin, list) {
  try {
    const o = new URL(origin)
    return list.includes(o.origin)
  } catch {
    return false
  }
}

function preflightResponse(origin, allowed, request) {
  const h = new Headers()
  if (origin && isOriginAllowed(origin, allowed)) {
    const acrh = request.headers.get('Access-Control-Request-Headers')
    h.set('Access-Control-Allow-Origin', origin)
    h.append('Vary', 'Origin')
    h.set('Access-Control-Allow-Credentials', 'true')
    h.set('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS')
    h.set(
      'Access-Control-Allow-Headers',
      acrh || 'Authorization,Content-Type,X-Client-Version,X-Client-Revision,X-CSRF-Token,X-CSRFToken',
    )
    h.set('Access-Control-Max-Age', '86400')
  }
  return new Response(null, { status: 204, headers: h })
}

function withCors(resp, origin, allowed) {
  const h = new Headers(resp.headers)
  if (origin && isOriginAllowed(origin, allowed)) {
    h.set('Access-Control-Allow-Origin', origin)
    const vary = h.get('Vary')
    h.set('Vary', vary ? `${vary}, Origin` : 'Origin')
    h.set('Access-Control-Allow-Credentials', 'true')
  }
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h })
}

function applyCorsHeaders(headers, origin, allowed) {
  if (origin && isOriginAllowed(origin, allowed)) {
    headers.set('Access-Control-Allow-Origin', origin)
    const vary = headers.get('Vary')
    headers.set('Vary', vary ? `${vary}, Origin` : 'Origin')
    headers.set('Access-Control-Allow-Credentials', 'true')
  } else {
    headers.delete('Access-Control-Allow-Origin')
    headers.delete('Access-Control-Allow-Credentials')
  }
}

function extractCookieDomain(host) {
  const parts = String(host).split('.')
  if (parts.length >= 2) return '.' + parts.slice(-2).join('.')
  return host
}

function rewriteCookiesRobust(srcHeaders, dstHeaders, cookieDomain) {
  // Collect all real Set-Cookie occurrences
  const cookies = []
  srcHeaders.forEach((v, k) => {
    if (k.toLowerCase() === 'set-cookie') cookies.push(v)
  })
  if (!cookies.length) return

  dstHeaders.delete('Set-Cookie')

  for (let c of cookies) {
    let v = c

    // Normalize Domain
    if (/;\s*Domain=/i.test(v)) {
      v = v.replace(/;\s*Domain=[^;]*/i, `; Domain=${cookieDomain}`)
    } else {
      v += `; Domain=${cookieDomain}`
    }

    // Force Path=/
    if (/;\s*Path=/i.test(v)) {
      v = v.replace(/;\s*Path=[^;]*/i, '; Path=/')
    } else {
      v += '; Path=/'
    }

    // Ensure Secure/HttpOnly
    if (!/;\s*Secure/i.test(v)) v += '; Secure'
    if (!/;\s*HttpOnly/i.test(v)) v += '; HttpOnly'

    // SameSite by cookie name
    if (/^refresh_token=/i.test(v)) {
      v = v.replace(/;\s*SameSite=[^;]*/i, '')
      v += '; SameSite=None'
    } else if (/^access_token=/i.test(v)) {
      v = v.replace(/;\s*SameSite=[^;]*/i, '')
      v += '; SameSite=Lax'
    }

    dstHeaders.append('Set-Cookie', v)
  }
}
