# Tabla de Códigos de Error — Validadores Fiscales

| Código | Severidad | Descripción | Campos Afectados | Acción Sugerida |
|--------|-----------|-------------|------------------|-----------------|
| **INVALID_TAX_ID_FORMAT** | error | Formato de identificación fiscal inválido | `tax_id`, `issuer_tax_id`, `supplier_tax_id` | Verifica que el RUC/NIF/CIF cumpla con el formato requerido del país |
| **INVALID_TAX_ID_CHECKSUM** | error | Dígito verificador incorrecto en identificación fiscal | `tax_id`, `issuer_tax_id`, `supplier_tax_id` | Revisa que el número sea correcto o regenera el dígito de control |
| **INVALID_TAX_RATE** | error | Tasa de impuesto inválida para el país | `tax_rate`, `iva_rate`, `ice_rate` | Ajusta la tasa al valor oficial vigente en el país |
| **TOTALS_MISMATCH** | error | Los totales no cuadran (base + impuesto ≠ total) | `net_amount`, `tax_amount`, `total_amount` | Recalcula los importes o revisa los redondeos |
| **INVALID_DATE_FORMAT** | error | Formato de fecha inválido | `invoice_date`, `transaction_date`, `expense_date` | Convierte la fecha al formato esperado (ISO 8601 o DD/MM/YYYY) |
| **MISSING_REQUIRED_FIELD** | error | Campo obligatorio faltante | Cualquier campo requerido | Proporciona un valor para el campo requerido |
| **EMPTY_VALUE** | error | Campo no puede estar vacío | Cualquier campo | Ingresa un valor no vacío |
| **INVALID_INVOICE_NUMBER_FORMAT** | error | Formato de número de factura inválido | `invoice_number` | Ajusta el número al formato requerido del país |
| **INVALID_CLAVE_ACCESO** | error | Clave de acceso SRI inválida (Ecuador) | `clave_acceso` | Regenera la clave de acceso con el algoritmo módulo 11 |
| **INVALID_CURRENCY** | error | Código de moneda inválido (ISO 4217) | `currency` | Usa un código de 3 letras según ISO 4217 (USD, EUR, etc.) |
| **FUTURE_DATE** | warning | La fecha no puede ser futura | Campos de fecha | Verifica que la fecha sea correcta |
| **NEGATIVE_AMOUNT** | error | El importe no puede ser negativo | Campos monetarios | Usa valores positivos o crea un documento de ajuste |

## Formatos por País

### Ecuador (EC)

#### RUC (Registro Único de Contribuyentes)
- **Formato**: 13 dígitos numéricos
- **Estructura**: 
  - Posiciones 1-2: Provincia (01-24)
  - Posición 3: Tipo (0-5: natural, 6: pública, 9: jurídica)
  - Posiciones 4-12: Número secuencial
  - Posición 13: Dígito verificador (módulo 11)
- **Ejemplos válidos**: 
  - `1713175071001` (persona natural)
  - `1792146739001` (jurídica)
  - `1760001550001` (pública)

#### Número de Factura
- **Formato**: `XXX-XXX-XXXXXXXXX`
- **Estructura**:
  - 3 dígitos: Establecimiento
  - 3 dígitos: Punto de emisión
  - 9 dígitos: Secuencial
- **Ejemplo válido**: `001-001-000000123`

#### Clave de Acceso SRI
- **Formato**: 49 dígitos numéricos
- **Estructura**:
  - Posiciones 1-8: Fecha de emisión (ddmmaaaa)
  - Posiciones 9-10: Tipo de comprobante (01: factura)
  - Posiciones 11-23: RUC del emisor
  - Posiciones 24-25: Tipo de ambiente (01: pruebas, 02: producción)
  - Posiciones 26-28: Serie (establecimiento)
  - Posiciones 29-31: Serie (punto emisión)
  - Posiciones 32-40: Número de comprobante
  - Posiciones 41-48: Código numérico
  - Posición 49: Dígito verificador (módulo 11)
- **Ejemplo válido**: `0801202501179214673900110010010000000011234567818`

#### Tasas de IVA
- **Vigentes**: 0%, 12%, 15%
- **ICE (categoría específica)**: 5%, 10%, 15%, 20%, 25%, 30%, 35%, 75%, 100%, 150%, 300%

---

### España (ES)

#### NIF (Número de Identificación Fiscal)
- **Formato**: 8 dígitos + 1 letra de control
- **Algoritmo**: Letra según módulo 23
- **Ejemplos válidos**: `12345678Z`, `87654321X`

#### NIE (Número de Identidad de Extranjero)
- **Formato**: Letra inicial (X/Y/Z) + 7 dígitos + 1 letra de control
- **Ejemplos válidos**: `X1234567L`, `Y9876543R`

#### CIF (Código de Identificación Fiscal)
- **Formato**: Letra inicial (A-W) + 7 dígitos + 1 dígito/letra de control
- **Letra inicial indica**:
  - A-J: Sociedades (A: SA, B: SL, etc.)
  - K-W: Otros (N: entidades extranjeras, Q: organismos públicos, etc.)
- **Ejemplos válidos**: `A12345674`, `B87654321`

#### Número de Factura
- **Formato**: Alfanumérico libre, hasta 30 caracteres
- **Caracteres permitidos**: A-Z, 0-9, `-`, `/`
- **Ejemplos válidos**: `FAC-2025-001`, `2025/123`, `A1234567890`, `INV-001-2025`

#### Tasas de IVA
- **Vigentes**: 
  - 0% (exento)
  - 4% (superreducido)
  - 10% (reducido)
  - 21% (general)

---

## Performance

- **Target**: < 10ms por validación completa de un item
- **Medición**: Incluye validación de tax_id + tax_rates + invoice_number
- **Tests**: `test_*_validator.py::TestPerformance`

---

## Extensibilidad

Para añadir un nuevo país:

1. Crear clase `XXValidator(CountryValidator)` en `country_validators.py`
2. Implementar métodos abstractos: `validate_tax_id`, `validate_tax_rates`, `validate_invoice_number`
3. Usar `self._create_error(code, field, params)` para generar errores del catálogo
4. Añadir nuevos códigos al `ERROR_CATALOG` si es necesario
5. Registrar en `get_validator_for_country()`
6. Crear tests en `test_xx_validator.py`

---

## Referencias

- **Ecuador SRI**: https://www.sri.gob.ec/
- **España AEAT**: https://www.agenciatributaria.es/
- **ISO 4217 (Currency codes)**: https://www.iso.org/iso-4217-currency-codes.html
- **ISO 8601 (Date format)**: https://www.iso.org/iso-8601-date-and-time-format.html
