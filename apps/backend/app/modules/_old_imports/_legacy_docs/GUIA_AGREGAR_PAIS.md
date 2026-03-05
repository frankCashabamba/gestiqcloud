# Guía Rápida: Agregar Soporte para Nuevo País

Proceso step-by-step para agregar validación de un nuevo país al importador.

## 🎯 Ejemplo: Agregar soporte Argentina (AR)

Tiempo estimado: **2-3 horas**

---

## Paso 1: Crear Validador (30 min)

### Archivo: `app/modules/imports/validators/country_validators.py`

Busca la clase `ESValidator` y agrega después:

```python
class ARValidator(CountryValidator):
    """Validador para Argentina (AFIP)."""

    # Tasas IVA válidas en Argentina
    VALID_IVA_RATES = [0.0, 10.5, 21.0, 27.0]

    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """
        Valida CUIT de Argentina (11 dígitos).
        Formato: XX.XXX.XXX-X
        """
        errors = []

        # Limpiar formato (puede venir con o sin puntos)
        cleaned = tax_id.replace(".", "").replace("-", "")

        # Validar que sean 11 dígitos
        if not re.match(r'^\d{11}$', cleaned):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_FORMAT",
                    "tax_id",
                    {"tax_id": tax_id, "country": "AR"}
                )
            )
            return errors

        # Validar dígito verificador AFIP
        if not self._validate_cuit_dv(cleaned):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_CHECK_DIGIT",
                    "tax_id",
                    {"tax_id": tax_id, "country": "AR"}
                )
            )

        return errors

    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Valida tasas IVA para Argentina."""
        errors = []

        for rate in rates:
            if rate not in self.VALID_IVA_RATES:
                errors.append(
                    self._create_error(
                        "INVALID_TAX_RATE",
                        "tax_rate",
                        {
                            "rate": rate,
                            "country": "AR",
                            "valid_rates": ", ".join(str(r) for r in self.VALID_IVA_RATES)
                        }
                    )
                )

        return errors

    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """
        Valida número de comprobante AFIP.
        Formato: XXX-XX-XXXXXXXX (punto-sucursal-número)
        """
        errors = []

        # Formato flexible: XXX-XX-XXXXXXXX o similar
        if not re.match(r'^\d{1,3}-\d{1,2}-\d{1,8}$', number):
            errors.append(
                self._create_error(
                    "INVALID_INVOICE_NUMBER",
                    "invoice_number",
                    {"number": number, "country": "AR"}
                )
            )

        return errors

    @staticmethod
    def _validate_cuit_dv(cuit: str) -> bool:
        """
        Valida dígito verificador del CUIT usando algoritmo AFIP.

        Algoritmo:
        1. Multiplicar cada dígito (izq a der) por [5,4,3,2,7,6,5,4,3,2]
        2. Sumar resultados
        3. DV = 11 - (suma % 11)
        4. Si DV = 11, DV = 0
        5. Si DV = 10, es inválido
        """
        multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

        suma = sum(
            int(digit) * mult
            for digit, mult in zip(cuit[:10], multiplicadores)
        )

        dv_calculado = 11 - (suma % 11)

        if dv_calculado == 11:
            dv_calculado = 0
        elif dv_calculado == 10:
            return False  # Inválido

        return int(cuit[10]) == dv_calculado
```

---

## Paso 2: Registrar en Factory (5 min)

### Archivo: `app/modules/imports/validators/country_validators.py`

Busca la función `get_validator_for_country()` y actualiza:

```python
def get_validator_for_country(country: str) -> Optional[CountryValidator]:
    """Factory para obtener validador según país."""
    validators = {
        "EC": ECValidator,
        "ES": ESValidator,
        "AR": ARValidator,  # ← AGREGAR AQUÍ
    }
    validator_class = validators.get(country.upper())
    return validator_class() if validator_class else None
```

---

## Paso 3: Agregar Códigos de Error (10 min)

### Archivo: `app/modules/imports/validators/error_catalog.py`

Busca el diccionario `ERROR_CATALOG` y agrega estos errores:

```python
ERROR_CATALOG = {
    # ... errores existentes ...

    # Errores Argentina (agregar estos)
    "INVALID_TAX_ID_FORMAT": {
        "severity": "error",
        "message_template": (
            "Formato CUIT inválido: {tax_id} (país: {country}). "
            "Esperado: XX.XXX.XXX-X (11 dígitos)"
        ),
    },
    "INVALID_TAX_ID_CHECK_DIGIT": {
        "severity": "error",
        "message_template": (
            "Dígito verificador inválido en CUIT {tax_id} (país: {country})"
        ),
    },
    "INVALID_TAX_RATE": {
        "severity": "error",
        "message_template": (
            "Tasa de IVA {rate}% no válida para {country}. "
            "Válidas: {valid_rates}%"
        ),
    },
    "INVALID_INVOICE_NUMBER": {
        "severity": "error",
        "message_template": (
            "Número de comprobante inválido para {country}: {number}. "
            "Esperado formato: XXX-XX-XXXXXXXX"
        ),
    },
}
```

---

## Paso 4: Escribir Tests (30 min)

### Archivo: `tests/modules/imports/validators/test_ar_validator.py` (NUEVO)

Crea este archivo nuevo:

```python
"""Tests para validador Argentina."""

import pytest
from app.modules.imports.validators.country_validators import (
    ARValidator,
    get_validator_for_country,
)


class TestARValidatorTaxId:
    """Tests de validación CUIT."""

    def test_valid_cuit(self):
        """CUIT válido según AFIP."""
        validator = ARValidator()
        # CUIT real: 20-12345678-1 (formato con formato de ejemplo válido)
        errors = validator.validate_tax_id("20123456789")  # Ajustar con CUIT real válido
        assert len(errors) == 0, f"CUIT válido fue rechazado: {errors}"

    def test_valid_cuit_with_format(self):
        """CUIT válido con puntos y guiones."""
        validator = ARValidator()
        errors = validator.validate_tax_id("20.12345678-9")
        assert len(errors) == 0, f"CUIT formateado fue rechazado: {errors}"

    def test_invalid_cuit_too_short(self):
        """CUIT con menos de 11 dígitos."""
        validator = ARValidator()
        errors = validator.validate_tax_id("1234567")
        assert len(errors) > 0
        assert any("formato" in e.message.lower() for e in errors)

    def test_invalid_cuit_check_digit(self):
        """CUIT con dígito verificador incorrecto."""
        validator = ARValidator()
        errors = validator.validate_tax_id("20123456780")  # Último dígito incorrecto
        assert len(errors) > 0
        assert any("dígito verificador" in e.message.lower() for e in errors)

    def test_invalid_cuit_non_numeric(self):
        """CUIT con caracteres no numéricos (sin puntos/guiones)."""
        validator = ARValidator()
        errors = validator.validate_tax_id("2012345678A")
        assert len(errors) > 0


class TestARValidatorTaxRates:
    """Tests de validación tasas IVA."""

    def test_valid_iva_0(self):
        """IVA 0% es válido."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([0.0])
        assert len(errors) == 0

    def test_valid_iva_10_5(self):
        """IVA 10.5% es válido."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([10.5])
        assert len(errors) == 0

    def test_valid_iva_21(self):
        """IVA 21% es válido (estándar Argentina)."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([21.0])
        assert len(errors) == 0

    def test_valid_iva_27(self):
        """IVA 27% es válido (aumentado)."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([27.0])
        assert len(errors) == 0

    def test_valid_multiple_rates(self):
        """Múltiples tasas válidas."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([0.0, 10.5, 21.0, 27.0])
        assert len(errors) == 0

    def test_invalid_iva_12(self):
        """IVA 12% no es válido en Argentina."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([12.0])
        assert len(errors) > 0
        assert any("no válida" in e.message.lower() for e in errors)

    def test_invalid_iva_15(self):
        """IVA 15% no es válido en Argentina."""
        validator = ARValidator()
        errors = validator.validate_tax_rates([15.0])
        assert len(errors) > 0


class TestARValidatorInvoiceNumber:
    """Tests de validación número comprobante."""

    def test_valid_invoice_number_standard(self):
        """Número de comprobante estándar."""
        validator = ARValidator()
        errors = validator.validate_invoice_number("001-01-00000001")
        assert len(errors) == 0

    def test_valid_invoice_number_other_format(self):
        """Otro número válido."""
        validator = ARValidator()
        errors = validator.validate_invoice_number("002-15-99999999")
        assert len(errors) == 0

    def test_invalid_invoice_number_no_format(self):
        """Sin formato de comprobante."""
        validator = ARValidator()
        errors = validator.validate_invoice_number("123456789")
        assert len(errors) > 0

    def test_invalid_invoice_number_wrong_separators(self):
        """Separadores incorrectos."""
        validator = ARValidator()
        errors = validator.validate_invoice_number("001/01/00000001")
        assert len(errors) > 0


class TestARValidatorFactory:
    """Tests del factory de validadores."""

    def test_get_ar_validator(self):
        """Obtener validador Argentina del factory."""
        validator = get_validator_for_country("AR")
        assert isinstance(validator, ARValidator)

    def test_get_ar_validator_lowercase(self):
        """Factory es case-insensitive."""
        validator = get_validator_for_country("ar")
        assert isinstance(validator, ARValidator)

    def test_get_ar_validator_uppercase(self):
        """Factory es case-insensitive (mayúsculas)."""
        validator = get_validator_for_country("AR")
        assert isinstance(validator, ARValidator)


class TestARValidatorIntegration:
    """Tests de integración con documentos completos."""

    def test_validate_complete_invoice_argentina(self):
        """Validar factura completa Argentina."""
        from app.modules.imports.domain.canonical_schema import validate_canonical

        doc = {
            "doc_type": "invoice",
            "country": "AR",
            "currency": "ARS",
            "issue_date": "2025-01-15",
            "invoice_number": "001-01-00000123",
            "vendor": {
                "name": "Proveedor SA",
                "tax_id": "20123456789",
                "country": "AR",
            },
            "totals": {
                "subtotal": 100.0,
                "tax": 21.0,
                "total": 121.0,
                "tax_breakdown": [
                    {"code": "IVA21-AR", "rate": 21.0, "amount": 21.0}
                ],
            },
        }

        # Validar estructura canónica
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Falla validación canónica: {errors}"

        # Validar con country validator
        validator = get_validator_for_country("AR")
        cuit_errors = validator.validate_tax_id(doc["vendor"]["tax_id"])
        assert len(cuit_errors) == 0, f"CUIT inválido: {cuit_errors}"

        rate_errors = validator.validate_tax_rates([21.0])
        assert len(rate_errors) == 0, f"Tasa inválida: {rate_errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Paso 5: Ejecutar Tests (10 min)

```bash
cd /c/Users/pc_cashabamba/Documents/GitHub/proyecto/apps/backend

# Tests unitarios del nuevo validador
python -m pytest tests/modules/imports/validators/test_ar_validator.py -v

# Tests de integración (Fase C completa)
python -m pytest tests/modules/imports/test_fase_c_integration.py -v

# Todos los tests de imports
python -m pytest tests/modules/imports/ -v
```

---

## Paso 6: Verificar Integración (10 min)

### Código de prueba manual

```python
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.validators.country_validators import get_validator_for_country
from app.modules.imports.domain.handlers_router import HandlersRouter

# Documento Argentina
doc = {
    "doc_type": "invoice",
    "country": "AR",
    "currency": "ARS",
    "issue_date": "2025-01-15",
    "invoice_number": "001-01-00000123",
    "vendor": {
        "name": "Proveedor",
        "tax_id": "20123456789"
    },
    "totals": {"subtotal": 100.0, "tax": 21.0, "total": 121.0},
}

# 1. Validar estructura
is_valid, errors = validate_canonical(doc)
print(f"✅ Estructura válida: {is_valid}")

# 2. Validar país
ar_validator = get_validator_for_country("AR")
cuit_errors = ar_validator.validate_tax_id("20123456789")
print(f"✅ CUIT válido: {len(cuit_errors) == 0}")

rate_errors = ar_validator.validate_tax_rates([21.0])
print(f"✅ Tasas válidas: {len(rate_errors) == 0}")

# 3. Despachar a handler
handler = HandlersRouter.get_handler_for_type("invoice")
target = HandlersRouter.get_target_for_type("invoice")
print(f"✅ Handler: {handler.__name__}")
print(f"✅ Destino: {target}")
```

---

## Paso 7: Documentar (10 min)

Añade a `FASE_C_VALIDADORES_PAISES.md` una nueva sección:

```markdown
## 2.3 Implementación: Argentina (AFIP)

**Ubicación:** `validators/country_validators.py`

**Reglas:**
- **CUIT:** 11 dígitos con validación de dígito verificador (algoritmo AFIP)
- **Tasas IVA válidas:** 0%, 10.5%, 21%, 27%
- **Formato comprobante:** XXX-XX-XXXXXXXX
- **Monedas:** ARS, USD

**Test:** `tests/modules/imports/validators/test_ar_validator.py`
```

---

## ✅ Checklist Final

- [ ] `ARValidator` creada en `country_validators.py`
- [ ] Registrada en `get_validator_for_country()`
- [ ] Códigos de error agregados a `error_catalog.py`
- [ ] Tests completos en `test_ar_validator.py`
- [ ] Todos los tests pasan (pytest)
- [ ] Documentación actualizada en `FASE_C_VALIDADORES_PAISES.md`
- [ ] Manual testing exitoso
- [ ] Git commit (opcional)

---

## 📚 Referencia Rápida

### Algoritmos por País

#### Argentina - CUIT
```
DV = 11 - ((d₀×5 + d₁×4 + d₂×3 + ... + d₉×2) % 11)
Si DV=11 → DV=0
Si DV=10 → Inválido
```

#### Ecuador - RUC
```
Validar provincia (d₀d₁) + secuencia + tipo persona + verificador
```

#### España - NIF/CIF
```
Cálculo módulo 23 para letra de NIF
```

---

## 🆘 Troubleshooting

### Tests fallan en imports
```bash
# Verificar PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"
pytest tests/modules/imports/validators/test_ar_validator.py -v
```

### Error "ModuleNotFoundError"
```bash
# Desde directorio backend
python -m pytest tests/modules/imports/validators/test_ar_validator.py -v
```

### Dígito verificador incorrecto
- Revisar algoritmo AFIP (paso 1, función `_validate_cuit_dv`)
- Usar CUITs de prueba reales de AFIP
- Validar que multiplicadores sean `[5,4,3,2,7,6,5,4,3,2]`

---

## ➡️ Próximos Pasos

Una vez completado Argentina:
1. Repetir proceso para **Brasil (CNPJ)**
2. Repetir para **Colombia (NIT)**
3. Repetir para **Perú (RUC)**

**Tiempo total por país:** 2-3 horas
**Tiempo acumulado 5 países:** ~12-15 horas

---

*Para preguntas, ver `FASE_C_VALIDADORES_PAISES.md`*
