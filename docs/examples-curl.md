# Ejemplos HTTP (curl)

Variables recomendadas:
```bash
API=http://localhost:8000
ADMIN_USER=ADMIN
ADMIN_PASS=secret
TENANT_USER=USER
TENANT_PASS=secret
TENANT_SLUG=kusi-panaderia
```

## Auth (tenant)
```bash
# Login tenant
curl -i -X POST "$API/api/v1/tenant/auth/login" \
  -H "Content-Type: application/json" \
  --data "{\"identificador\":\"$TENANT_USER\",\"password\":\"$TENANT_PASS\"}" \
  -c tenant.cookies

# Refresh
curl -i -X POST "$API/api/v1/tenant/auth/refresh" -b tenant.cookies -c tenant.cookies
```

## Auth (admin)
```bash
# Login admin
curl -i -X POST "$API/api/v1/admin/auth/login" \
  -H "Content-Type: application/json" \
  --data "{\"identificador\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" \
  -c admin.cookies

# Listar empresas
curl -s "$API/api/v1/admin/empresas" -b admin.cookies
```

## Settings/campos dinámicos
```bash
curl -s "$API/api/v1/company/settings/fields?module=clientes&empresa=$TENANT_SLUG" -b tenant.cookies
```

## Imports
```bash
# Crear batch
BATCH=$(curl -s -H "Authorization: Bearer $(cat token.txt 2>/dev/null)" \
  -H "Content-Type: application/json" \
  -d '{"source_type":"receipts","origin":"ocr"}' \
  "$API/api/v1/imports/batches" | jq -r '.id')

# Ingestar filas
curl -s -H "Authorization: Bearer $(cat token.txt 2>/dev/null)" \
  -H "Content-Type: application/json" \
  -d '{"rows":[{"sku":"123","name":"Prod"}]}' \
  "$API/api/v1/imports/batches/$BATCH/ingest"

# Validar y promover
curl -s -X POST -H "Authorization: Bearer $(cat token.txt 2>/dev/null)" \
  "$API/api/v1/imports/batches/$BATCH/validate"
curl -s -X POST -H "Authorization: Bearer $(cat token.txt 2>/dev/null)" \
  "$API/api/v1/imports/batches/$BATCH/promote"
```

## E-invoicing (ejemplo básico)
```bash
# Listar estados de facturas (ajusta path según módulo)
curl -s "$API/api/v1/einvoicing" -b tenant.cookies
```

## Pagos (ajustar proveedor y payload)
```bash
# Intento de pago (Stripe/Payphone/Kushki según backend)
curl -s -X POST "$API/api/v1/payments/intent" \
  -H "Content-Type: application/json" \
  -b tenant.cookies \
  --data '{"amount":1000,"currency":"USD","provider":"stripe"}'
```

Notas:
- Usa `-k` si pruebas contra HTTPS con certificados self-signed.
- Para cookies, los workers en Cloudflare reescriben dominio/SameSite en producción; en local no aplica.
