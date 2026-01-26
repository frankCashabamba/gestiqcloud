# API Contracts - GestiqCloud

**Versión API:** v1
**Base URL:** `/api/v1`
**Última actualización:** 2026-01-17

---

## Tabla de Contenidos

1. [Convenciones Generales](#convenciones-generales)
2. [Headers Requeridos](#headers-requeridos)
3. [Estructura de Respuestas](#estructura-de-respuestas)
4. [Códigos de Error](#códigos-de-error)
5. [Contratos por Módulo](#contratos-por-módulo)
   - [Auth](#auth)
   - [Products](#products)
   - [Sales](#sales)
   - [Clients](#clients)
6. [Política de Versionado](#política-de-versionado)

---

## Convenciones Generales

### Prefijos de Rutas

| Prefijo | Scope | Descripción |
|---------|-------|-------------|
| `/api/v1/tenant/*` | Tenant | Endpoints para usuarios de empresa |
| `/api/v1/admin/*` | Admin | Endpoints para superusuarios |
| `/api/v1/*` | Universal | Endpoints genéricos (compat layer) |

### Formato de Datos

- **Content-Type:** `application/json`
- **Encoding:** UTF-8
- **IDs:** UUID v4 (string format) para la mayoría de recursos
- **Fechas:** ISO 8601 (`YYYY-MM-DD` o `YYYY-MM-DDTHH:mm:ssZ`)
- **Montos:** Números decimales (float)

### Naming Conventions

- Endpoints en **snake_case** o **kebab-case**
- Request/Response bodies en **snake_case**
- Query parameters en **snake_case**

---

## Headers Requeridos

### Para Endpoints Protegidos

| Header | Requerido | Descripción |
|--------|-----------|-------------|
| `Authorization` | Sí* | `Bearer {access_token}` |
| `X-CSRF-Token` | Sí (mutaciones) | Token CSRF para POST/PUT/DELETE |
| `Content-Type` | Sí | `application/json` |
| `Accept-Language` | No | Código de idioma (`es`, `en`) |

> *El access token también puede enviarse via cookie `access_token`.

### Cookies Automáticas

| Cookie | HttpOnly | Descripción |
|--------|----------|-------------|
| `access_token` | Sí | JWT de acceso (15 min) |
| `refresh_token` | Sí | JWT de refresh (7 días) |
| `csrf_token` | No | Token CSRF legible por JS |
| `session_id` | Sí | ID de sesión del servidor |

---

## Estructura de Respuestas

### Respuesta Exitosa (Single Resource)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Producto Ejemplo",
  "price": 99.99,
  "created_at": "2026-01-17T10:30:00Z"
}
```

### Respuesta Exitosa (Lista)

```json
[
  { "id": "...", "name": "Item 1" },
  { "id": "...", "name": "Item 2" }
]
```

### Respuesta con Paginación

```json
{
  "items": [...],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

### Respuesta de Error

```json
{
  "detail": "error_code"
}
```

O con más contexto:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Códigos de Error

### HTTP Status Codes

| Código | Significado | Uso |
|--------|-------------|-----|
| `200` | OK | Operación exitosa |
| `201` | Created | Recurso creado |
| `204` | No Content | Eliminación exitosa |
| `400` | Bad Request | Datos inválidos |
| `401` | Unauthorized | Token inválido/expirado |
| `403` | Forbidden | Sin permisos |
| `404` | Not Found | Recurso no existe |
| `409` | Conflict | Conflicto (duplicado) |
| `422` | Unprocessable Entity | Error de validación |
| `429` | Too Many Requests | Rate limit excedido |
| `500` | Internal Server Error | Error del servidor |

### Códigos de Error Internos

| Código | Módulo | Descripción |
|--------|--------|-------------|
| `invalid_credentials` | Auth | Usuario/contraseña incorrectos |
| `too_many_attempts` | Auth | Rate limit de login |
| `token_expired` | Auth | Token expirado |
| `refresh_token_reused` | Auth | Reuso de refresh token (familia revocada) |
| `missing_tenant` | General | Tenant no identificado |
| `items_required` | Sales | Orden sin items |
| `order_not_found` | Sales | Orden no existe |
| `order_not_confirmed` | Sales | Estado inválido para operación |
| `confirmation_required` | Products | Purge sin confirmación |
| `weak_password` | Auth | Contraseña < 8 caracteres |

---

## Contratos por Módulo

### Auth

#### POST `/api/v1/tenant/auth/login`

Autenticación de usuarios de empresa.

**Request Body:**

```json
{
  "identificador": "usuario@email.com",
  "password": "contraseña123"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `identificador` | string | Sí | Email o username |
| `password` | string | Sí | Contraseña |

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "scope": "tenant",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "empresa_slug": "mi-empresa",
  "plantilla": "retail",
  "is_company_admin": true
}
```

**Cookies Seteadas:**
- `access_token` (HttpOnly, Lax)
- `refresh_token` (HttpOnly, Strict, path=/api/v1/tenant/auth/refresh)
- `csrf_token` (Lax)

**Errores Posibles:**

| Código | Detail | Descripción |
|--------|--------|-------------|
| 401 | `invalid_credentials` | Credenciales incorrectas |
| 429 | `too_many_attempts` | Rate limit (10 req/min) |
| 500 | `claims_error` | Error interno al construir claims |
| 500 | `refresh_family_error` | Error al crear familia de tokens |

---

#### POST `/api/v1/tenant/auth/refresh`

Renueva el access token usando el refresh token.

**Request:** Sin body. Usa cookie `refresh_token`.

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Cookies Seteadas:**
- `access_token` (renovado)
- `refresh_token` (rotado)

**Errores Posibles:**

| Código | Detail | Descripción |
|--------|--------|-------------|
| 401 | `token_expired` | Refresh token expirado |
| 401 | `refresh_token_reused` | Token reusado, familia revocada |

---

#### POST `/api/v1/tenant/auth/logout`

Cierra sesión y revoca tokens.

**Request:** Sin body. Usa cookie `refresh_token`.

**Response 200:**

```json
{
  "ok": true
}
```

> Siempre retorna 200, operación idempotente.

---

#### GET `/api/v1/tenant/auth/csrf`

Obtiene un token CSRF para operaciones POST/PUT/DELETE.

**Response 200:**

```json
{
  "ok": true,
  "csrfToken": "abc123..."
}
```

**Cookies Seteadas:**
- `csrf_token` (Lax, HttpOnly=false)

---

#### POST `/api/v1/tenant/auth/set-password`

Establece contraseña desde token de email (password reset).

**Request Body:**

```json
{
  "token": "email-token-from-link",
  "password": "nuevaContraseña123"
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `token` | string | Sí | Token de email válido (24h) |
| `password` | string | Sí | Mínimo 8 caracteres |

**Response 200:**

```json
{
  "ok": true,
  "email": "user@email.com",
  "username": "usuario1"
}
```

**Errores Posibles:**

| Código | Detail | Descripción |
|--------|--------|-------------|
| 400 | `invalid_request` | Campos vacíos |
| 400 | `weak_password` | Password < 8 chars |
| 400 | `invalid_or_expired_token` | Token inválido/expirado |
| 404 | `user_not_found` | Usuario no existe |

---

### Products

Prefijo: `/api/v1/tenant/products`

**Autenticación requerida:** Sí (Bearer token, scope: tenant)

---

#### GET `/products`

Lista productos del tenant.

**Query Parameters:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `limit` | int | 100 | Máximo resultados |
| `offset` | int | 0 | Saltar N resultados |
| `active` | bool | - | Filtrar por activos |
| `category_id` | uuid | - | Filtrar por categoría |
| `search` | string | - | Búsqueda por nombre/SKU |

**Response 200:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Producto A",
    "price": 99.99,
    "stock": 50.0,
    "unit": "unit",
    "sku": "PROD-001",
    "category": "Electrónica",
    "category_id": "...",
    "description": "Descripción del producto",
    "tax_rate": 21.0,
    "cost_price": 50.0,
    "active": true,
    "product_metadata": {}
  }
]
```

---

#### POST `/products`

Crea un nuevo producto.

**Request Body:**

```json
{
  "name": "Nuevo Producto",
  "price": 199.99,
  "stock": 100.0,
  "unit": "kg",
  "category": "Alimentos",
  "sku": "PROD-002",
  "description": "Descripción",
  "tax_rate": 10.5,
  "cost_price": 80.0,
  "active": true,
  "product_metadata": { "origen": "local" }
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `name` | string | Sí | min_length=1 |
| `price` | float | Sí | >= 0 |
| `stock` | float | Sí | >= 0 |
| `unit` | string | No | default="unit" |
| `category` | string | No | Nombre de categoría |
| `category_id` | uuid | No | ID de categoría existente |
| `sku` | string | No | Código único |
| `description` | string | No | - |
| `tax_rate` | float | No | >= 0 |
| `cost_price` | float | No | >= 0 |
| `active` | bool | No | default=true |
| `product_metadata` | object | No | Metadatos libres |

**Response 201:** Producto creado (mismo schema que GET)

---

#### GET `/products/{product_id}`

Obtiene un producto por ID.

**Response 200:** Objeto producto

**Errores:**

| Código | Detail |
|--------|--------|
| 404 | `not_found` |

---

#### PUT `/products/{product_id}`

Actualiza un producto.

**Request Body:** Mismos campos que POST, todos opcionales.

**Response 200:** Producto actualizado

---

#### DELETE `/products/{product_id}`

Elimina un producto.

**Response 204:** Sin contenido

---

#### POST `/products/purge`

Elimina masivamente productos (destructivo).

**Request Body:**

```json
{
  "confirm": "PURGE",
  "include_stock": true,
  "include_categories": true,
  "dry_run": false
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `confirm` | string | Sí | Debe ser "PURGE" |
| `include_stock` | bool | No | Incluir stock_moves/items |
| `include_categories` | bool | No | Incluir categorías |
| `dry_run` | bool | No | Solo simular |

**Response 200:**

```json
{
  "dry_run": false,
  "counts": {
    "stock_moves": 150,
    "stock_items": 50,
    "products": 200,
    "product_categories": 10
  },
  "deleted": {
    "stock_moves": 150,
    "stock_items": 50,
    "products": 200,
    "product_categories": 10
  }
}
```

**Requiere:** Role owner/manager/admin

---

#### POST `/products/bulk/active`

Activa/desactiva productos masivamente.

**Request Body:**

```json
{
  "ids": ["uuid1", "uuid2"],
  "active": true
}
```

**Response 200:**

```json
{
  "updated": 2
}
```

---

#### POST `/products/bulk/category`

Asigna categoría a múltiples productos.

**Request Body:**

```json
{
  "ids": ["uuid1", "uuid2"],
  "category_name": "Nueva Categoría"
}
```

**Response 200:**

```json
{
  "updated": 2,
  "category_created": true,
  "category_name": "Nueva Categoría"
}
```

---

### Sales

Prefijo: `/api/v1/tenant/sales_orders`

**Autenticación requerida:** Sí (Bearer token, scope: tenant)

---

#### GET `/sales_orders`

Lista órdenes de venta.

**Query Parameters:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `status` | string | - | Filtrar por estado |
| `customer_id` | int | - | Filtrar por cliente |
| `limit` | int | 100 | Máximo resultados |
| `offset` | int | 0 | Saltar N resultados |

**Response 200:**

```json
[
  {
    "id": 1,
    "status": "draft",
    "customer_id": 123,
    "currency": "ARS"
  }
]
```

---

#### POST `/sales_orders`

Crea una orden de venta.

**Request Body:**

```json
{
  "customer_id": 123,
  "currency": "ARS",
  "items": [
    {
      "product_id": 1,
      "qty": 5.0,
      "unit_price": 100.0
    }
  ]
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `customer_id` | int | No | ID del cliente |
| `currency` | string | No | Código de moneda |
| `items` | array | Sí | Lista de items |
| `items[].product_id` | int | Sí | ID del producto |
| `items[].qty` | float | Sí | Cantidad (> 0) |
| `items[].unit_price` | float | No | Precio unitario |

**Response 201:**

```json
{
  "id": 1,
  "status": "draft",
  "customer_id": 123,
  "currency": "ARS"
}
```

**Errores:**

| Código | Detail |
|--------|--------|
| 400 | `items_required` |

---

#### GET `/sales_orders/{order_id}`

Obtiene una orden por ID.

**Response 200:** Objeto orden

**Errores:**

| Código | Detail |
|--------|--------|
| 404 | `Orden no encontrada` |

---

#### POST `/sales_orders/{order_id}/confirm`

Confirma una orden (reserva stock).

**Request Body:**

```json
{
  "warehouse_id": "uuid-warehouse"
}
```

**Response 200:** Orden con `status: "confirmed"`

**Errores:**

| Código | Detail |
|--------|--------|
| 400 | `invalid_status` |
| 400 | `no_items` |
| 404 | `order_not_found` |

---

### Deliveries

Prefijo: `/api/v1/tenant/deliveries`

---

#### POST `/deliveries/`

Crea un delivery para una orden confirmada.

**Request Body:**

```json
{
  "order_id": 1
}
```

**Response 201:**

```json
{
  "id": 1,
  "status": "pending"
}
```

---

#### POST `/deliveries/{delivery_id}/deliver`

Ejecuta la entrega (consume stock).

**Request Body:**

```json
{
  "warehouse_id": 1
}
```

**Response 200:**

```json
{
  "delivery_id": 1,
  "status": "done"
}
```

---

### Clients

Prefijo: `/api/v1/tenant/clientes`

**Autenticación requerida:** Sí (Bearer token, scope: tenant)

---

#### GET `/clientes`

Lista todos los clientes del tenant.

**Response 200:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Cliente Ejemplo",
    "identificacion": "20-12345678-9",
    "email": "cliente@email.com",
    "phone": "+54 11 1234-5678",
    "address": "Av. Corrientes 1234",
    "localidad": "CABA",
    "state": "Buenos Aires",
    "pais": "Argentina",
    "codigo_postal": "1043",
    "is_wholesale": false
  }
]
```

---

#### POST `/clientes`

Crea un nuevo cliente.

**Request Body:**

```json
{
  "name": "Nuevo Cliente",
  "identificacion": "20-12345678-9",
  "email": "nuevo@email.com",
  "phone": "+54 11 5555-5555",
  "address": "Calle 123",
  "localidad": "Palermo",
  "state": "Buenos Aires",
  "pais": "Argentina",
  "codigo_postal": "1425",
  "is_wholesale": true
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `name` | string | Sí | min_length=1 |
| `identificacion` | string | No | CUIT/DNI |
| `email` | string | No | - |
| `phone` | string | No | - |
| `address` | string | No | - |
| `localidad` | string | No | - |
| `state` | string | No | Provincia |
| `pais` | string | No | - |
| `codigo_postal` | string | No | - |
| `is_wholesale` | bool | No | default=false |

**Response 200:** Cliente creado

---

#### GET `/clientes/{cliente_id}`

Obtiene un cliente por ID.

**Response 200:** Objeto cliente

**Errores:**

| Código | Detail |
|--------|--------|
| 404 | `Cliente no encontrado` |

---

#### PUT `/clientes/{cliente_id}`

Actualiza un cliente.

**Request Body:** Mismos campos que POST

**Response 200:** Cliente actualizado

---

#### DELETE `/clientes/{cliente_id}`

Elimina un cliente.

**Response 200:**

```json
{
  "ok": true
}
```

---

## Política de Versionado

### Esquema de Versiones

La API usa **versionado por URL**: `/api/v{major}/...`

- **Major version (v1, v2):** Cambios incompatibles
- Dentro de una versión major, la API es **backward compatible**

### Cuándo Incrementar Versión

| Cambio | Acción |
|--------|--------|
| Nuevo endpoint | Agregar sin cambiar versión |
| Nuevo campo opcional en response | Agregar sin cambiar versión |
| Nuevo query parameter opcional | Agregar sin cambiar versión |
| Eliminar endpoint | **Nueva versión major** |
| Cambiar tipo de campo | **Nueva versión major** |
| Renombrar campo requerido | **Nueva versión major** |
| Cambiar semántica de endpoint | **Nueva versión major** |

### Deprecation Timeline

1. **Anuncio (D+0):** Documentar deprecación, agregar header `Deprecation`
2. **Aviso (D+90):** Agregar header `Sunset` con fecha de remoción
3. **Remoción (D+180):** Endpoint retorna 410 Gone

### Headers de Deprecación

```http
Deprecation: true
Sunset: Sat, 17 Jul 2026 23:59:59 GMT
Link: </api/v2/resource>; rel="successor-version"
```

### Backward Compatibility

Garantizamos que dentro de v1:

- Los endpoints existentes siguen funcionando
- Los campos existentes mantienen su tipo y significado
- Los códigos de error mantienen su semántica
- Los nuevos campos en responses son opcionales

### Soporte de Versiones

| Versión | Estado | Soporte hasta |
|---------|--------|---------------|
| v1 | **Activa** | - |

---

## Rate Limiting

### Límites por Endpoint

| Endpoint | Límite | Ventana |
|----------|--------|---------|
| `/auth/login` | 10 req | 60 seg |
| `/auth/password-reset` | 5 req | 300 seg |
| General (autenticado) | 100 req | 60 seg |
| General (público) | 20 req | 60 seg |

### Headers de Rate Limit

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705488000
Retry-After: 45
```

---

## Changelog

### v1.0.0 (2026-01-17)

- Documentación inicial de contratos API
- Módulos: Auth, Products, Sales, Clients
