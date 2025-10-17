# Ejemplos de Uso — Validadores Fiscales por País

## 1. Validación directa por país

```python
from app.modules.imports.validators import ECValidator, ESValidator

# Ecuador
ec_validator = ECValidator()

# RUC
errors = ec_validator.validate_tax_id("1713175071001")
if errors:
    for err in errors:
        print(f"[{err['code']}] {err['field']}: {err['message']}")

# Número de factura
errors = ec_validator.validate_invoice_number("001-001-000000123")

# Tasas de IVA
errors = ec_validator.validate_tax_rates([0.0, 12.0, 15.0])

# Clave de acceso SRI
errors = ec_validator.validate_clave_acceso("0801202501179214673900110010010000000011234567818")

# España
es_validator = ESValidator()

# NIF/CIF/NIE
errors = es_validator.validate_tax_id("12345678Z")  # NIF
errors = es_validator.validate_tax_id("A12345674")  # CIF
errors = es_validator.validate_tax_id("X1234567L")  # NIE

# Número de factura
errors = es_validator.validate_invoice_number("FAC-2025-001")

# Tasas de IVA
errors = es_validator.validate_tax_rates([0.0, 4.0, 10.0, 21.0])
```

## 2. Factory pattern

```python
from app.modules.imports.validators import get_validator_for_country

# Obtener validador según país
validator = get_validator_for_country("EC")  # ECValidator
validator = get_validator_for_country("ES")  # ESValidator

# Usar dinámicamente
def validate_document(doc: dict, country: str):
    try:
        validator = get_validator_for_country(country)
        errors = []
        
        if doc.get("tax_id"):
            errors.extend(validator.validate_tax_id(doc["tax_id"]))
        
        if doc.get("invoice_number"):
            errors.extend(validator.validate_invoice_number(doc["invoice_number"]))
        
        if doc.get("tax_rates"):
            errors.extend(validator.validate_tax_rates(doc["tax_rates"]))
        
        return errors
    except ValueError as e:
        return [{"code": "UNSUPPORTED_COUNTRY", "message": str(e)}]
```

## 3. Integración con `validate_invoices`

```python
from app.modules.imports.validators import validate_invoices

# Ecuador
invoice_ec = {
    "invoice_number": "001-001-000000123",
    "invoice_date": "2025-01-15",
    "issuer_tax_id": "1713175071001",
    "net_amount": 100.0,
    "tax_amount": 12.0,
    "total_amount": 112.0,
    "tax_rate": 12.0,
    "currency": "USD",
}

errors = validate_invoices(invoice_ec, country="EC")
if errors:
    for err in errors:
        print(f"{err['field']}: {err['msg']}")

# España
invoice_es = {
    "invoice_number": "FAC-2025-001",
    "invoice_date": "2025-01-15",
    "issuer_tax_id": "12345678Z",
    "net_amount": 100.0,
    "tax_amount": 21.0,
    "total_amount": 121.0,
    "tax_rate": 21.0,
    "currency": "EUR",
}

errors = validate_invoices(invoice_es, country="ES")
```

## 4. Crear validador para nuevo país

```python
from app.modules.imports.validators.country_validators import CountryValidator
from typing import List

class MXValidator(CountryValidator):
    """Validador para México (SAT)."""
    
    VALID_IVA_RATES = [0.0, 8.0, 16.0]
    
    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """Valida RFC mexicano."""
        errors = []
        
        if not re.match(r"^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$", tax_id):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_FORMAT",
                    "tax_id",
                    {
                        "value": tax_id,
                        "expected_format": "RFC con homoclave (ej: XAXX010101000)",
                    },
                )
            )
        
        return errors
    
    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Valida tasas de IVA para México."""
        errors = []
        for rate in rates:
            if rate not in self.VALID_IVA_RATES:
                errors.append(
                    self._create_error(
                        "INVALID_TAX_RATE",
                        "tax_rate",
                        {
                            "rate": rate,
                            "country": "México",
                            "valid_rates": ", ".join(f"{r}%" for r in self.VALID_IVA_RATES),
                        },
                    )
                )
        return errors
    
    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """Valida UUID de CFDI."""
        errors = []
        if not re.match(r"^[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}$", number, re.IGNORECASE):
            errors.append(
                self._create_error(
                    "INVALID_INVOICE_NUMBER_FORMAT",
                    "invoice_number",
                    {
                        "value": number,
                        "expected_format": "UUID CFDI (ej: 12345678-1234-1234-1234-123456789012)",
                    },
                )
            )
        return errors

# Registrar en factory
def get_validator_for_country(country_code: str) -> CountryValidator:
    validators = {
        "EC": ECValidator,
        "ES": ESValidator,
        "MX": MXValidator,  # ← Nuevo
    }
    # ...
```

## 5. Batch validation para imports

```python
from app.modules.imports.validators import get_validator_for_country

def validate_batch(invoices: list[dict], country: str):
    """Valida un lote de facturas con reporte agregado."""
    validator = get_validator_for_country(country)
    
    results = {
        "valid": [],
        "invalid": [],
        "stats": {"total": 0, "errors": 0, "warnings": 0}
    }
    
    for idx, invoice in enumerate(invoices):
        errors = []
        
        if invoice.get("issuer_tax_id"):
            errors.extend(validator.validate_tax_id(invoice["issuer_tax_id"]))
        
        if invoice.get("invoice_number"):
            errors.extend(validator.validate_invoice_number(invoice["invoice_number"]))
        
        if invoice.get("tax_rates"):
            errors.extend(validator.validate_tax_rates(invoice["tax_rates"]))
        
        results["stats"]["total"] += 1
        
        if errors:
            error_count = sum(1 for e in errors if e["severity"] == "error")
            warning_count = sum(1 for e in errors if e["severity"] == "warning")
            
            results["stats"]["errors"] += error_count
            results["stats"]["warnings"] += warning_count
            
            results["invalid"].append({
                "index": idx,
                "invoice": invoice,
                "errors": errors
            })
        else:
            results["valid"].append(invoice)
    
    return results

# Uso
batch = [
    {"issuer_tax_id": "1713175071001", "invoice_number": "001-001-000000123"},
    {"issuer_tax_id": "1713175071009", "invoice_number": "FAC-001"},  # Errores
]

results = validate_batch(batch, "EC")
print(f"Válidas: {len(results['valid'])}/{results['stats']['total']}")
print(f"Errores: {results['stats']['errors']}, Warnings: {results['stats']['warnings']}")
```

## 6. Acceso al catálogo de errores

```python
from app.modules.imports.validators.error_catalog import ERROR_CATALOG

# Ver definición de error
error_def = ERROR_CATALOG["INVALID_TAX_ID_FORMAT"]
print(error_def["message_template"])
print(error_def["suggested_action"])

# Buscar errores por severidad
critical_errors = [
    code for code, def_ in ERROR_CATALOG.items()
    if def_["severity"] == "error"
]

# Crear mensaje de ayuda
def explain_error(code: str, params: dict = None):
    """Genera mensaje de ayuda para un código de error."""
    if code not in ERROR_CATALOG:
        return f"Error desconocido: {code}"
    
    error_def = ERROR_CATALOG[code]
    message = error_def["message_template"]
    
    if params:
        message = message.format(**params)
    
    return f"""
ERROR: {message}
ACCIÓN SUGERIDA: {error_def["suggested_action"]}
"""

# Uso
print(explain_error("INVALID_TAX_ID_FORMAT", {
    "value": "12345",
    "expected_format": "13 dígitos (RUC Ecuador)"
}))
```
