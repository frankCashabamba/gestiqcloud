# Diseño contable POS Panadería
_(FastAPI + React + PostgreSQL, multi-tenant)_

---

## 1. Objetivo general

Implementar la integración entre el **POS de panadería** y el **módulo de contabilidad**, de forma:

- **Multi-tenant**: cada empresa tiene su propio plan de cuentas y configuración.
- **Configurable**: las cuentas contables **no están hardcodeadas**, el contable/propietario las define.
- **Automática**: al cerrar un turno de caja en el POS se genera un **asiento contable**.
- **Profesional**: uso de tablas claras, validaciones, control de permisos y auditoría.

---

## 2. Alcance funcional

1. **Plan Contable por tenant**
   - CRUD de cuentas contables (código, nombre, tipo, jerarquía).
   - Cada tenant (empresa) tiene su propio catálogo.

2. **Parámetros contables del tenant**
   - Pantalla para asignar qué cuenta contable usar para:
     - Caja (efectivo POS)
     - Bancos / Tarjetas
     - Ventas panadería
     - IVA repercutido
     - Pérdidas y mermas
   - Los parámetros se usan al generar asientos desde el POS.

3. **Medios de pago**
   - Configuración de medios de pago del POS (EFECTIVO, TARJETA, VALE, LINK, etc.).
   - Cada medio de pago se asocia a una cuenta contable concreta.

4. **Contabilización del POS**
   - Generación de **asiento resumen por cierre de turno** (recomendado).
   - Opcional: soporte futuro para asientos por ticket.
   - Uso del **IVA configurado del tenant** (no hardcodeado).

5. **Módulo contable**
   - Librerías y vistas ya existentes:
     - Dashboard
     - Movimientos
     - Libro Diario
     - Libro Mayor
     - Pérdidas y Ganancias
     - Plan Contable
     - Conciliación bancaria
   - Se alimentan con los asientos generados.

---

## 3. Modelo de datos (PostgreSQL)

> Nota: todas las tablas llevan `tenant_id` para garantizar multi-tenant.

### 3.1. Tabla `accounts` – Plan contable

Catálogo de cuentas contables de la empresa.

```sql
CREATE TABLE accounts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL,

  code            VARCHAR(20) NOT NULL,         -- Ej: '570', '7000001'
  name            VARCHAR(255) NOT NULL,        -- Ej: 'Caja', 'Ventas panadería'
  account_type    VARCHAR(20) NOT NULL,         -- 'ASSET', 'LIABILITY', 'INCOME', 'EXPENSE', 'EQUITY'
  parent_id       UUID NULL,                    -- Para jerarquía (cuenta padre)
  is_active       BOOLEAN NOT NULL DEFAULT true,

  created_at      TIMESTAMP NOT NULL DEFAULT now(),
  updated_at      TIMESTAMP NOT NULL DEFAULT now(),

  CONSTRAINT uq_accounts_tenant_code UNIQUE (tenant_id, code),
  FOREIGN KEY (parent_id) REFERENCES accounts(id)
);
```

**Responsable de datos**: el contable o administrador del tenant, a través de la UI de “Plan Contable”.
**El software no inventa códigos**, solo los guarda y los usa.

---

### 3.2. Tabla `tenant_accounting_settings` – Parámetros contables

Asocia conceptos del sistema a cuentas contables concretas.

```sql
CREATE TABLE tenant_accounting_settings (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id               UUID NOT NULL UNIQUE,

  cash_account_id         UUID NOT NULL,   -- Caja del POS
  bank_account_id         UUID NOT NULL,   -- Bancos / Tarjetas
  sales_bakery_account_id UUID NOT NULL,   -- Ventas panadería
  vat_output_account_id   UUID NOT NULL,   -- IVA repercutido
  loss_account_id         UUID NULL,       -- Pérdidas / Mermas

  created_at              TIMESTAMP NOT NULL DEFAULT now(),
  updated_at              TIMESTAMP NOT NULL DEFAULT now(),

  FOREIGN KEY (cash_account_id)         REFERENCES accounts(id),
  FOREIGN KEY (bank_account_id)         REFERENCES accounts(id),
  FOREIGN KEY (sales_bakery_account_id) REFERENCES accounts(id),
  FOREIGN KEY (vat_output_account_id)   REFERENCES accounts(id),
  FOREIGN KEY (loss_account_id)         REFERENCES accounts(id)
);
```

---

### 3.3. Tabla `payment_methods` – Medios de pago

Cada medio de pago del POS se mapea a una cuenta contable.

```sql
CREATE TABLE payment_methods (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL,

  name           VARCHAR(50) NOT NULL,   -- 'EFECTIVO', 'TARJETA', 'VALE', etc.
  description    VARCHAR(255),
  account_id     UUID NOT NULL,          -- Cuenta contable asociada
  is_active      BOOLEAN NOT NULL DEFAULT true,

  created_at     TIMESTAMP NOT NULL DEFAULT now(),
  updated_at     TIMESTAMP NOT NULL DEFAULT now(),

  FOREIGN KEY (account_id) REFERENCES accounts(id),
  CONSTRAINT uq_payment_methods_tenant_name UNIQUE (tenant_id, name)
);
```

---

### 3.4. Tabla `vat_rates` – Tipos de IVA (si no existe ya)

```sql
CREATE TABLE vat_rates (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL,

  name           VARCHAR(50) NOT NULL,   -- 'IVA General', 'IVA Reducido', etc.
  rate           NUMERIC(5, 2) NOT NULL, -- 21.00, 10.00, etc.
  is_default     BOOLEAN NOT NULL DEFAULT false,

  created_at     TIMESTAMP NOT NULL DEFAULT now(),
  updated_at     TIMESTAMP NOT NULL DEFAULT now()
);
```

---

### 3.5. Tabla `journal_entries` – Asientos

```sql
CREATE TABLE journal_entries (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL,

  date           DATE NOT NULL,
  description    VARCHAR(255) NOT NULL,
  origin_module  VARCHAR(50) NOT NULL,   -- 'POS_BAKERY', 'MANUAL', etc.
  origin_ref     VARCHAR(100),           -- ej: id del cierre de turno

  created_at     TIMESTAMP NOT NULL DEFAULT now(),
  updated_at     TIMESTAMP NOT NULL DEFAULT now()
);
```

---

### 3.6. Tabla `journal_entry_lines` – Líneas del asiento

```sql
CREATE TABLE journal_entry_lines (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  journal_entry_id   UUID NOT NULL,
  account_id         UUID NOT NULL,

  debit              NUMERIC(18, 2) NOT NULL DEFAULT 0,
  credit             NUMERIC(18, 2) NOT NULL DEFAULT 0,
  line_number        INTEGER NOT NULL,

  FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id),
  FOREIGN KEY (account_id)       REFERENCES accounts(id)
);
```

Reglas a nivel de aplicación:

- En una línea:
  - `debit == 0` **o** `credit == 0` (nunca ambos > 0).
- En un asiento:
  - `SUM(debit) == SUM(credit)`.

---

## 4. Vistas de frontend (React)

### 4.1. Plan Contable

**Ruta sugerida:** `/accounting/chart-of-accounts`

**Funcionalidad:**

- Listado de cuentas (`accounts`) filtrado por `tenant_id`:
  - Código
  - Nombre
  - Tipo
  - Activa / Inactiva
- Acciones:
  - Crear cuenta
  - Editar cuenta
  - Activar / desactivar

**Formulario de creación / edición:**

- Código (input de texto)
- Nombre
- Tipo (select: Activo / Pasivo / Ingreso / Gasto / Patrimonio)
- Cuenta padre (select opcional que lista otras cuentas)
- Estado (checkbox “Activa”)

---

### 4.2. Configuración Contable POS

**Ruta sugerida:** `/accounting/settings/pos`

Formulario que guarda/lee `tenant_accounting_settings`.

Campos (tipo select con búsqueda):

- **Cuenta de Caja POS**
  - Fuente: `accounts` de tipo `ASSET`.
- **Cuenta de Bancos / Tarjetas**
- **Cuenta de Ventas Panadería**
- **Cuenta de IVA Repercutido**
- **Cuenta de Pérdidas y Mermas**

Validaciones:

- No permitir guardar si falta alguna cuenta obligatoria.
- Mostrar mensajes claros:
  - Ej.: “Debes seleccionar una cuenta de ventas panadería”.

---

### 4.3. Gestión de Medios de Pago

**Ruta sugerida:** `/accounting/settings/payment-methods`

**Listado:**

- Nombre del medio (EFECTIVO, TARJETA, VALE…)
- Cuenta contable asociada (`code - name`)
- Estado (activo/inactivo)

**Formulario:**

- Nombre (string)
- Descripción (opcional)
- Cuenta contable (select)
- Checkbox “Activo”

Se guarda en la tabla `payment_methods`.

---

## 5. Flujo POS → Contabilidad

### 5.1. Datos que envía el cierre de turno del POS

Ejemplo de payload:

```json
{
  "tenant_id": "uuid-tenant",
  "turn_close_id": "uuid-turn",
  "date": "2025-02-20",
  "total_net": 100.00,
  "total_vat": 21.00,
  "total_gross": 121.00,
  "by_payment_method": [
    { "method_name": "EFECTIVO", "amount": 50.00 },
    { "method_name": "TARJETA",  "amount": 71.00 }
  ],
  "loss_amount": 2.00
}
```

- `total_net` = base imponible (sin IVA).
- `total_vat` = IVA.
- `total_gross` = importe total cobrado.
- `by_payment_method` = desglose por forma de cobro.
- `loss_amount` = diferencia / merma detectada en el cierre (si aplica).

---

### 5.2. Algoritmo de contabilización (backend)

Pasos generales:

1. **Cargar configuración del tenant**
   - `tenant_accounting_settings`:
     - `cash_account_id`
     - `bank_account_id`
     - `sales_bakery_account_id`
     - `vat_output_account_id`
     - `loss_account_id`
   - Si no existe -> error:
     - “Falta configurar parámetros contables del POS para este tenant”.

2. **Cargar medios de pago**
   - Desde `payment_methods` por `tenant_id`.
   - Validar que cada `method_name` recibido tenga una cuenta asociada.

3. **Validaciones numéricas**
   - Verificar que:
     - `SUM(by_payment_method.amount)` sea coherente con `total_gross`.
     - Si hay `loss_amount`, ajustar según criterio:
       - p.ej. `SUM(by_payment_method) = total_gross ± loss_amount`.

4. **Crear asiento (`journal_entries`)**
   - `date` = fecha de cierre.
   - `description` = “Cierre turno panadería {turn_close_id}”.
   - `origin_module` = `POS_BAKERY`.
   - `origin_ref` = `turn_close_id`.

5. **Crear líneas (`journal_entry_lines`)**

   - Líneas de ingresos e IVA (HABER):
     - Ventas panadería → `sales_bakery_account_id`
       - `credit = total_net`
       - `debit = 0`
     - IVA repercutido → `vat_output_account_id`
       - `credit = total_vat`
       - `debit = 0`

   - Líneas de cobro (DEBE), por cada medio de pago:
     - Buscar `payment_methods.method_name`.
     - Usar `payment_methods.account_id` como `account_id`.
       - `debit = amount`
       - `credit = 0`

   - Si `loss_amount > 0` (pérdidas/mermas):
     - Cuenta de pérdidas/mermas → `loss_account_id`
       - `debit = loss_amount`
     - Contrapartida habitual → caja (`cash_account_id`)
       - `credit = loss_amount`
     - Ajustar según criterio del contable.

6. **Validación final**
   - Antes de confirmar, verificar:
     - `SUM(debit) == SUM(credit)`
   - Si no se cumple, no registrar el asiento y registrar/loggear el error.

---

## 6. Reglas de negocio y buenas prácticas

### 6.1. Multi-tenant

- Todas las consultas a tablas contables deben filtrar por `tenant_id`.
- Nunca mezclar datos de distintos tenants en resultados ni joins.

### 6.2. Permisos y roles

- Solo `ADMIN` / `ACCOUNTANT` pueden:
  - Crear / editar cuentas (`accounts`).
  - Modificar `tenant_accounting_settings`.
  - Configurar `payment_methods`.
- El POS / rol `CASHIER`:
  - Registra ventas y cierres.
  - Puede disparar la contabilización del cierre, pero **no cambiar cuentas**.

### 6.3. Auditoría

- Mantener siempre:
  - `created_at`, `updated_at`.
  - (Opcional) `created_by`, `updated_by` (usuario autenticado).
- Útil para trazabilidad en inspecciones contables.

### 6.4. UX / Mensajes

- En selects de cuentas, mostrar:
  - `code - name` (ej: `570 - Caja General`).
- Mensajes de error claros y de negocio:
  - “Debes crear al menos una cuenta contable antes de configurar el POS.”
  - “El medio de pago TARJETA no tiene cuenta contable asociada.”
  - “No se pudo generar el asiento porque las cuentas configuradas están incompletas.”

### 6.5. Migraciones y datos seed

- Crear migraciones (Alembic) para todas las tablas definidas.
- Opcionalmente, para entornos demo:
  - Seed con cuentas ejemplo:
    - 570 Caja
    - 572 Banco
    - 700 Ventas
    - 477 IVA repercutido
    - 678 Pérdidas y mermas
  - El usuario puede ajustar estos datos en producción.

---

## 7. Checklist de implementación

- [ ] Tablas creadas:
  - [ ] `accounts`
  - [ ] `tenant_accounting_settings`
  - [ ] `payment_methods`
  - [ ] `vat_rates`
  - [ ] `journal_entries`
  - [ ] `journal_entry_lines`
- [ ] CRUD de `accounts` (“Plan Contable”) implementado.
- [ ] Pantalla de “Configuración Contable POS” conectada a `tenant_accounting_settings`.
- [ ] Gestión de `payment_methods` operativa.
- [ ] Endpoint de contabilización de cierres de turno POS implementado.
- [ ] Validaciones:
  - [ ] Asientos siempre balanceados.
  - [ ] Configuración contable completa antes de permitir contabilizar.
  - [ ] Coherencia entre totales y desglose de medios de pago.
- [ ] Control de permisos por rol aplicado.
- [ ] Mensajes de error y feedback en frontend.
- [ ] Pruebas de flujo:
  1. Crear cuentas en Plan Contable.
  2. Configurar parámetros contables POS.
  3. Configurar medios de pago.
  4. Registrar y cerrar un turno en el POS.
  5. Ver asiento generado en Libro Diario / Movimientos.

---
