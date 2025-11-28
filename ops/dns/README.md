# DNS (Cloudflare)

## Zonas
- `gestiqcloud.com` (Cloudflare).

## Registros relevantes (ver archivos .txt en este directorio)
- CNAME/A para `admin.gestiqcloud.com` y `www.gestiqcloud.com` apuntando al Worker/Render según configuración actual.
- Otros subdominios listados en: `gestiqcloud.com.txt`, `cloudflare_dns_records.txt`, `gestiqcloud.com.cname-flattening.txt`.

## Operación
- Cambios vía Cloudflare Dashboard o API.
- Mantener alineadas las rutas del Worker con los registros.
- Documentar TTL y proxied (orange/grey) según entorno.
