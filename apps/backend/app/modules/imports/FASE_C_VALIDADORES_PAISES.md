# Fase C - Validadores por País y Handlers

Documentación completa de la arquitectura de validación por país/sector y enrutamiento a handlers en el módulo de importaciones.

## 1. Arquitectura General

### Flujo de Validación

```
Archivo → Parser → CanonicalDocument
                    ↓
         validate_canonical() [SPEC-1]
                    ↓
      Country-specific validators
         (ECValidator, ESValidator, ...)
                    ↓
         Validación de sectores/tipos
                    ↓
           ✅ o ❌ (errores)
```

### Flujo de Enrutamiento

```
CanonicalDocument + validaciones ✅
         ↓
  HandlersRouter.promote_canonical()
         ↓
   doc_type → Handler mapping
         ↓
   InvoiceHandler | BankHandler | ExpenseHandler | ProductHandler
         ↓
   Insert en tabla destino (invoices, bank_movements, expenses, inventory)
```

## 2. Validadores por País

### 2.1 Estructura Base

Todos los validadores heredan de `CountryValidator` en `validators/country_validators.py`:

```python
from abc import ABC, abstractmethod
from typing import List
from .error_catalog import ERROR_CATALOG, ValidationError

class CountryValidator(ABC):
    """Clase base para validadores fiscales por país."""
    
    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """Valida formato e integridad de identificación fiscal."""
        pass
    
    @abstractmethod
    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Valida que las tasas de impuesto sean legales."""
        pass
    
    @abstractmethod
    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """Valida formato de numeración de factura."""
        pass
```

### 2.2 Implementaciones Actuales

#### **ECValidator (Ecuador - SRI)**

**Ubicación:** `validators/country_validators.py`

**Reglas:**
- **RUC:** 13 dígitos con validación de dígito verificador (SRI)
- **Tasas IVA válidas:** 0%, 12%, 15%
- **Tasas ICE:** 5%, 10%, 15%, 20%, 25%, 30%, 35%, 75%, 100%
- **Formato factura:** `###-###-XXXXXXXXX` (establec-punto-secuencial)
- **Monedas:** USD, PEN, EUR, CAD

**Ejemplo de uso:**

```python
from app.modules.imports.validators.country_validators import ECValidator

validator = ECValidator()

# Validar RUC
errors = validator.validate_tax_id("1792012345001")
if not errors:
    print("RUC válido")

# Validar tasas de impuesto
errors = validator.validate_tax_rates([12.0, 5.0])  # IVA + ICE
if not errors:
    print("Tasas válidas para Ecuador")

# Validar formato de factura
errors = validator.validate_invoice_number("001-002-000000123")
if not errors:
    print("Número de factura válido")
```

#### **ESValidator (España)**

**Ubicación:** `validators/country_validators.py`

**Reglas:**
- **NIF/CIF:** Formato estándar español (8-9 caracteres alfanuméricos)
- **Tasas IVA válidas:** 0%, 4%, 10%, 21%
- **Formato factura:** Flexible (sin restricción de estructura)
- **Monedas:** EUR

**Uso:**

```python
from app.modules.imports.validators.country_validators import ESValidator

validator = ESValidator()

# Validar CIF/NIF
errors = validator.validate_tax_id("12345678Z")
if not errors:
    print("NIF válido")

# Validar tasas
errors = validator.validate_tax_rates([21.0])  # IVA estándar España
```

### 2.3 Agregar un Nuevo Validador por País

**Pasos:**

1. **Crear la clase en `validators/country_validators.py`:**

```python
class ARValidator(CountryValidator):
    """Validador para Argentina (AFIP)."""
    
    # Definir tasas válidas
    VALID_IVA_RATES = [0.0, 10.5, 21.0, 27.0]
    
    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """CUIT: 11 dígitos con validación de dígito verificador."""
        errors = []
        
        # Validar formato
        if not re.match(r'^\d{11}$', tax_id):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_FORMAT",
                    "tax_id",
                    {"tax_id": tax_id, "country": "AR"}
                )
            )
            return errors
        
        # Validar dígito verificador (algoritmo AFIP)
        if not self._validate_cuit_dv(tax_id):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_CHECK_DIGIT",
                    "tax_id",
                    {"tax_id": tax_id, "country": "AR"}
                )
            )
        
        return errors
    
    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Validar tasas IVA."""
        errors = []
        for rate in rates:
            if rate not in self.VALID_IVA_RATES:
                errors.append(
                    self._create_error(
                        "INVALID_TAX_RATE",
                        "tax_rate",
                        {"rate": rate, "country": "AR", "valid_rates": self.VALID_IVA_RATES}
                    )
                )
        return errors
    
    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """Validar número de comprobante."""
        # Implementar según normas AFIP
        return []
    
    def _validate_cuit_dv(self, cuit: str) -> bool:
        """Validar dígito verificador del CUIT."""
        # Implementar algoritmo AFIP
        pass
```

2. **Registrar en `get_validator_for_country()`:**

```python
def get_validator_for_country(country: str) -> Optional[CountryValidator]:
    """Factory para obtener validador según país."""
    validators = {
        "EC": ECValidator,
        "ES": ESValidator,
        "AR": ARValidator,  # ← Agregar aquí
    }
    validator_class = validators.get(country.upper())
    return validator_class() if validator_class else None
```

3. **Agregar códigos de error en `validators/error_catalog.py`:**

```python
ERROR_CATALOG = {
    # ... errores existentes ...
    "INVALID_TAX_RATE": {
        "severity": "error",
        "message_template": "Tasa de impuesto {rate} no válida para {country}. Válidas: {valid_rates}",
    },
    "INVALID_TAX_ID_CHECK_DIGIT": {
        "severity": "error",
        "message_template": "Dígito verificador inválido en {country} tax_id",
    },
}
```

4. **Escribir tests en `tests/modules/imports/validators/test_ar_validator.py`:**

```python
import pytest
from app.modules.imports.validators.country_validators import ARValidator

class TestARValidator:
    """Tests para validador de Argentina."""
    
    def test_validate_valid_cuit(self):
        """CUIT válido."""
        validator = ARValidator()
        errors = validator.validate_tax_id("20123456781")
        assert len(errors) == 0
    
    def test_validate_invalid_cuit_format(self):
        """CUIT con formato incorrecto."""
        validator = ARValidator()
        errors = validator.validate_tax_id("12345678")
        assert len(errors) > 0
    
    def test_validate_invalid_cuit_dv(self):
        """CUIT con dígito verificador incorrecto."""
        validator = ARValidator()
        errors = validator.validate_tax_id("20123456789")
        assert len(errors) > 0
```

## 3. Mapeo doc_type → Handlers

### 3.1 HandlersRouter

**Ubicación:** `domain/handlers_router.py`

Mapea tipos de documento a handlers:

```python
class HandlersRouter:
    
    HANDLER_MAP = {
        "invoice": InvoiceHandler,
        "expense_receipt": ExpenseHandler,
        "bank_tx": BankHandler,
        "product": ProductHandler,
        # Aliases
        "factura": InvoiceHandler,
        "recibo": ExpenseHandler,
        "transferencia": BankHandler,
    }
    
    ROUTING_TARGET_MAP = {
        "invoice": "invoices",
        "expense_receipt": "expenses",
        "bank_tx": "bank_movements",
        "product": "inventory",
    }
    
    @classmethod
    def promote_canonical(cls, db, tenant_id, canonical_doc, **kwargs):
        """Promocionar documento a tabla destino."""
        doc_type = canonical_doc.get("doc_type", "other")
        handler_class = cls.get_handler_for_type(doc_type)
        
        if not handler_class:
            return {"domain_id": None, "target": "unknown", "skipped": False}
        
        # Instanciar y ejecutar handler
        handler = handler_class()
        return handler.handle(db, tenant_id, canonical_doc, **kwargs)
```

### 3.2 Agregar un Nuevo Handler

**Pasos:**

1. **Crear clase en `domain/handlers.py`:**

```python
class ShipmentHandler:
    """Handler para envíos/logística."""
    
    def handle(self, db: Session, tenant_id: UUID, canonical_doc: Dict) -> PromoteResult:
        """
        Procesar documento de envío.
        
        Inserta en tabla de shipments con validaciones.
        """
        try:
            shipment_data = self._extract_shipment_data(canonical_doc)
            
            # Crear registro
            shipment = Shipment(
                tenant_id=tenant_id,
                **shipment_data
            )
            db.add(shipment)
            db.flush()
            
            return PromoteResult(
                domain_id=str(shipment.id),
                target="shipments",
                skipped=False,
            )
        except Exception as e:
            return PromoteResult(
                domain_id=None,
                target="shipments",
                skipped=False,
                error=str(e),
            )
    
    def _extract_shipment_data(self, canonical_doc: Dict) -> Dict:
        """Extraer datos relevantes del documento canónico."""
        return {
            "tracking_number": canonical_doc.get("shipment", {}).get("tracking"),
            "carrier": canonical_doc.get("shipment", {}).get("carrier"),
            "origin": canonical_doc.get("shipment", {}).get("origin"),
            "destination": canonical_doc.get("shipment", {}).get("destination"),
            "estimated_date": canonical_doc.get("shipment", {}).get("estimated_date"),
        }
```

2. **Registrar en HandlersRouter:**

```python
class HandlersRouter:
    HANDLER_MAP = {
        # ... existentes ...
        "shipment": ShipmentHandler,
    }
    
    ROUTING_TARGET_MAP = {
        # ... existentes ...
        "shipment": "shipments",
    }
```

3. **Agregar validación en `canonical_schema.py`:**

```python
def validate_canonical(data: dict) -> Tuple[bool, List[str]]:
    # ... validaciones existentes ...
    
    if doc_type == "shipment":
        errors.extend(_validate_shipment(data))
    
    # ...

def _validate_shipment(data: dict) -> List[str]:
    """Validar bloque shipment."""
    errors = []
    shipment = data.get("shipment", {})
    
    if not shipment.get("tracking_number"):
        errors.append("shipment: tracking_number es obligatorio")
    
    if not shipment.get("carrier"):
        errors.append("shipment: carrier es obligatorio")
    
    return errors
```

## 4. Flujo Completo: De Archivo a Base de Datos

### Ejemplo: Importar Factura Ecuador

```
1. Usuario sube XML de factura SRI
                ↓
2. Clasificador detecta: "invoice" + país = "EC"
                ↓
3. Parser XmlInvoiceParser.parse()
   → CanonicalDocument {
       doc_type: "invoice",
       country: "EC",
       invoice_number: "001-002-000123",
       vendor: {tax_id: "1792012345001"},
       totals: {tax_breakdown: [{rate: 12.0}]}
     }
                ↓
4. validate_canonical() ✅
                ↓
5. ECValidator.validate_tax_id() ✅
   ECValidator.validate_tax_rates() ✅
   ECValidator.validate_invoice_number() ✅
                ↓
6. HandlersRouter.promote_canonical()
   - doc_type "invoice" → InvoiceHandler
   - target: "invoices"
                ↓
7. InvoiceHandler.handle()
   → INSERT INTO invoices (tenant_id, number, vendor_id, total, ...)
                ↓
8. ✅ Factura importada en BD
```

### Código de Uso

```python
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.validators.country_validators import get_validator_for_country
from app.modules.imports.domain.handlers_router import HandlersRouter
from sqlalchemy.orm import Session
from uuid import UUID

def import_document(
    db: Session,
    tenant_id: UUID,
    canonical_doc: dict,
    country: str,
) -> dict:
    """Importar y promocionar documento."""
    
    # 1. Validación canónica
    is_valid, errors = validate_canonical(canonical_doc)
    if not is_valid:
        return {"success": False, "errors": errors}
    
    # 2. Validación por país (si aplica)
    country_validator = get_validator_for_country(country)
    if country_validator:
        vendor = canonical_doc.get("vendor", {})
        if vendor and vendor.get("tax_id"):
            errors = country_validator.validate_tax_id(vendor["tax_id"])
            if errors:
                return {"success": False, "errors": [e.message for e in errors]}
        
        if canonical_doc.get("totals", {}).get("tax_breakdown"):
            rates = [t["rate"] for t in canonical_doc["totals"]["tax_breakdown"]]
            errors = country_validator.validate_tax_rates(rates)
            if errors:
                return {"success": False, "errors": [e.message for e in errors]}
    
    # 3. Enrutamiento y promoción
    result = HandlersRouter.promote_canonical(
        db=db,
        tenant_id=tenant_id,
        canonical_doc=canonical_doc,
    )
    
    db.commit()
    
    return {
        "success": True,
        "domain_id": result["domain_id"],
        "target": result["target"],
    }
```

## 5. Catálogo de Errores

**Ubicación:** `validators/error_catalog.py`

Define errores reutilizables con templates:

```python
ERROR_CATALOG = {
    "INVALID_TAX_ID_FORMAT": {
        "severity": "error",
        "message_template": "Formato de identificación fiscal inválido: {tax_id} (país: {country})",
    },
    "INVALID_TAX_ID_CHECK_DIGIT": {
        "severity": "error",
        "message_template": "Dígito verificador inválido en {country} tax_id",
    },
    "INVALID_TAX_RATE": {
        "severity": "error",
        "message_template": "Tasa de impuesto {rate}% no válida para {country}",
    },
    "INVALID_INVOICE_NUMBER": {
        "severity": "error",
        "message_template": "Número de factura inválido según normativa {country}: {number}",
    },
}
```

## 6. Testing

### 6.1 Tests por País

- `tests/modules/imports/validators/test_ec_validator.py` - Ecuador
- `tests/modules/imports/validators/test_es_validator.py` - España
- `tests/modules/imports/validators/test_integration.py` - Integración

### 6.2 Tests de Handlers

```bash
pytest tests/modules/imports/test_promotion.py
```

### 6.3 Tests de Flujo Completo

```bash
pytest tests/modules/imports/integration/
```

## 7. Checklist de Implementación

### Para agregar soporte a un nuevo país:

- [ ] Crear validador en `validators/country_validators.py`
- [ ] Registrar en `get_validator_for_country()`
- [ ] Agregar códigos de error en `error_catalog.py`
- [ ] Escribir tests unitarios en `tests/modules/imports/validators/test_XX_validator.py`
- [ ] Documentar tasas válidas, formatos, etc.
- [ ] Agregar fixture de ejemplo en tests
- [ ] Actualizar este documento

## 8. Referencias

- [SPEC-1 Canonical Schema](canonical_schema.py)
- [Handlers](domain/handlers.py)
- [Validators](validators/__init__.py)
- [Country Validators](validators/country_validators.py)
- [Error Catalog](validators/error_catalog.py)
