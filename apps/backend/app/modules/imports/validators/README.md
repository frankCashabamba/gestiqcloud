# Validadores Fiscales por País — Resumen

## ✅ Archivos Creados

### Módulos Core
```
apps/backend/app/modules/imports/validators/
├── __init__.py                    # Exports públicos
├── country_validators.py          # Validadores EC/ES + Factory
├── error_catalog.py               # Catálogo de códigos de error
├── USAGE_EXAMPLES.md              # Ejemplos de uso completos
├── ERROR_CODES.md                 # Tabla de códigos y formatos
└── README.md                      # Este archivo
```

### Tests
```
apps/backend/tests/modules/imports/validators/
├── __init__.py
├── test_ec_validator.py           # 15 tests Ecuador (RUC, facturas, clave acceso)
├── test_es_validator.py           # 15 tests España (NIF/CIF/NIE, facturas)
└── test_integration.py            # 5 tests integración con validate_invoices()
```

### Actualizaciones
```
apps/backend/app/modules/imports/validators.py
  ← Actualizado para integrar validadores de país con parámetro `country`
```

---

## 🚀 Uso Rápido

### Validar factura completa (con país)
```python
from app.modules.imports.validators import validate_invoices

invoice = {
    "invoice_number": "001-001-000000123",
    "invoice_date": "2025-01-15",
    "issuer_tax_id": "1713175071001",
    "net_amount": 100.0,
    "tax_amount": 12.0,
    "total_amount": 112.0,
    "tax_rate": 12.0,
}

errors = validate_invoices(invoice, country="EC")
```

### Validar componentes individuales
```python
from app.modules.imports.validators import ECValidator, ESValidator

# Ecuador
ec = ECValidator()
errors = ec.validate_tax_id("1713175071001")              # RUC
errors = ec.validate_invoice_number("001-001-000000123")  # Factura
errors = ec.validate_tax_rates([0.0, 12.0])               # IVA
errors = ec.validate_clave_acceso("0801202501...")        # Clave SRI (49 dígitos)

# España
es = ESValidator()
errors = es.validate_tax_id("12345678Z")                  # NIF
errors = es.validate_invoice_number("FAC-2025-001")       # Factura
errors = es.validate_tax_rates([0.0, 21.0])               # IVA
```

### Factory dinámico
```python
from app.modules.imports.validators import get_validator_for_country

validator = get_validator_for_country("EC")  # o "ES"
errors = validator.validate_tax_id(tax_id)
```

---

## 📊 Tabla de Códigos de Error

| Código | Severidad | Mensaje | Acción Sugerida |
|--------|-----------|---------|-----------------|
| `INVALID_TAX_ID_FORMAT` | error | Formato de identificación fiscal inválido | Verifica el formato RUC/NIF/CIF |
| `INVALID_TAX_ID_CHECKSUM` | error | Dígito verificador incorrecto | Revisa o regenera el dígito de control |
| `INVALID_TAX_RATE` | error | Tasa de impuesto inválida | Ajusta a tasa oficial del país |
| `TOTALS_MISMATCH` | error | Totales no cuadran (base + impuesto ≠ total) | Recalcula importes o redondeos |
| `INVALID_DATE_FORMAT` | error | Formato de fecha inválido | Usa ISO 8601 o DD/MM/YYYY |
| `MISSING_REQUIRED_FIELD` | error | Campo obligatorio faltante | Proporciona valor para el campo |
| `EMPTY_VALUE` | error | Campo no puede estar vacío | Ingresa valor no vacío |
| `INVALID_INVOICE_NUMBER_FORMAT` | error | Formato de número de factura inválido | Ajusta al formato del país |
| `INVALID_CLAVE_ACCESO` | error | Clave de acceso SRI inválida (EC) | Regenera clave con módulo 11 |
| `INVALID_CURRENCY` | error | Código de moneda inválido | Usa ISO 4217 (USD, EUR, etc.) |
| `FUTURE_DATE` | warning | Fecha futura | Verifica que sea correcta |
| `NEGATIVE_AMOUNT` | error | Importe negativo | Usa valores positivos o nota de crédito |

**Total**: 12 códigos estables

---

## 🌍 Países Soportados

### Ecuador (EC)
- **RUC**: 13 dígitos, algoritmo módulo 11 (natural/jurídica/pública)
- **Factura**: `XXX-XXX-XXXXXXXXX` (estab-punto-secuencial)
- **Clave SRI**: 49 dígitos con checksum módulo 11
- **IVA**: 0%, 12%, 15%
- **ICE**: 5%, 10%, 15%, 20%, 25%, 30%, 35%, 75%, 100%, 150%, 300%

### España (ES)
- **NIF**: 8 dígitos + letra de control (módulo 23)
- **NIE**: X/Y/Z + 7 dígitos + letra
- **CIF**: Letra inicial + 7 dígitos + dígito/letra de control
- **Factura**: Alfanumérico libre, hasta 30 caracteres
- **IVA**: 0%, 4%, 10%, 21%

---

## 🔧 Extensibilidad

### Añadir nuevo país (ejemplo: México)

1. **Crear validador** en `country_validators.py`:
```python
class MXValidator(CountryValidator):
    VALID_IVA_RATES = [0.0, 8.0, 16.0]

    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        # Validar RFC
        ...

    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        ...

    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        # Validar UUID CFDI
        ...
```

2. **Registrar** en `get_validator_for_country()`:
```python
validators = {
    "EC": ECValidator,
    "ES": ESValidator,
    "MX": MXValidator,  # ← Nuevo
}
```

3. **Añadir tests** en `tests/.../test_mx_validator.py`

---

## ⚡ Performance

- **Target**: < 10ms por validación completa
- **Medición**: tax_id + tax_rates + invoice_number
- **Tests**: Incluyen `TestPerformance` en cada validador

---

## 📚 Referencias

- [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md) — Ejemplos detallados de integración
- [ERROR_CODES.md](./ERROR_CODES.md) — Tabla completa con formatos por país
- [SPEC-1](../spec_1_importador_documental_gestiq_cloud.md) — Especificación de Importador

---

## 🧪 Ejecutar Tests

```bash
# Todos los tests de validadores
pytest apps/backend/tests/modules/imports/validators/ -v

# Sólo Ecuador
pytest apps/backend/tests/modules/imports/validators/test_ec_validator.py -v

# Sólo España
pytest apps/backend/tests/modules/imports/validators/test_es_validator.py -v

# Integración
pytest apps/backend/tests/modules/imports/validators/test_integration.py -v

# Con cobertura
pytest apps/backend/tests/modules/imports/validators/ --cov=app.modules.imports.validators --cov-report=html
```

---

**Estado**: ✅ Implementado y listo para integración con SPEC-1 (Importador Documental)
