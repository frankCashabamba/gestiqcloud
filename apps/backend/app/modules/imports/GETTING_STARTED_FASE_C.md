# Getting Started: Fase C - Validación y Handlers

Guía de inicio rápido para continuar con Fase C después de Fase B.

## 🎯 Objetivo de Fase C

Validar los datos parseados con el esquema canónico (SPEC-1) y enrutarlos a sus correspondientes handlers para inserción en tablas destino.

---

## 📋 Requisitos Previos

### Verificar que Fase B está completa:
```bash
# 1. Verificar que los parsers están registrados
python3 -c "from app.modules.imports.parsers import registry; print(len(registry.list_parsers()))"
# Debe retornar: 10

# 2. Verificar que se pueden obtener parsers
python3 -c "from app.modules.imports.parsers import registry; print(registry.get_parser('csv_products') is not None)"
# Debe retornar: True
```

### Documentación relevante:
- ✅ IMPORTADOR_PLAN.md (Plan general)
- ✅ FASE_B_NUEVOS_PARSERS.md (Parsers disponibles)
- ✅ PARSER_REGISTRY.md (Referencia de parsers)

---

## 🏗️ Arquitectura de Fase C

```
Parser Output (Fase B)
    ↓
Canonical Validation (Fase C)
    ↓
Document Type Detection
    ↓
Handler Selection
    ↓
Promotion to Destination Table
```

---

## 📚 Tareas Principales de Fase C

### 1. Extender Esquema Canónico

**Archivo**: `app/modules/imports/domain/canonical_schema.py`

**Qué agregar**:
- Soporte para `doc_type='product'`
- Soporte para `doc_type='expense'`
- Validadores específicos para cada tipo

**Estructura esperada**:
```python
class CanonicalDocument:
    """Documento canónico base (SPEC-1)."""
    doc_type: str  # 'invoice', 'bank_tx', 'product', 'expense'
    
    # Campos específicos por tipo
    # ...

class ProductDocument(CanonicalDocument):
    """Extensión para productos."""
    nombre: str
    precio: float
    cantidad: float
    sku: Optional[str]
    categoria: str

class ExpenseDocument(CanonicalDocument):
    """Extensión para gastos."""
    description: str
    amount: float
    category: Optional[str]
    vendor: Optional[str]
    date: Optional[str]
```

### 2. Crear Handlers

**Archivo**: `app/modules/imports/domain/handlers.py` (actualizar)

**Handlers a crear**:
- `ProductHandler` - Insertar/actualizar productos
- `ExpenseHandler` - Insertar gastos/recibos

**Interfaz esperada**:
```python
class ProductHandler:
    def validate(self, doc: CanonicalDocument) -> bool:
        """Validar documento antes de insertar."""
        pass
    
    def promote(self, doc: CanonicalDocument, tenant_id: str) -> str:
        """Insertar producto y retornar ID."""
        pass

class ExpenseHandler:
    def validate(self, doc: CanonicalDocument) -> bool:
        pass
    
    def promote(self, doc: CanonicalDocument, tenant_id: str) -> str:
        pass
```

### 3. Crear Router de Handlers

**Archivo**: `app/modules/imports/domain/handlers_router.py`

**Funcionalidad**:
```python
def get_handler(doc_type: str):
    """Obtener handler para un tipo de documento."""
    handlers = {
        'invoice': InvoiceHandler(),
        'bank_tx': BankHandler(),
        'product': ProductHandler(),      # NUEVO
        'expense': ExpenseHandler(),       # NUEVO
    }
    return handlers.get(doc_type)
```

### 4. Crear Validadores por País/Sector

**Ubicación**: `app/modules/imports/validators/`

**Archivos a crear**:
- `validators_product.py` - Validadores para productos
- `validators_expense.py` - Validadores para gastos
- `validators_by_country.py` - Validadores por país

---

## 🔄 Flujo de Fase C

### Paso 1: Parser genera resultado (Fase B)
```python
parser = registry.get_parser("csv_products")
result = parser["handler"]("products.csv")
# result["products"] = [{doc_type: 'product', ...}, ...]
```

### Paso 2: Validar cada item con esquema canónico (Fase C)
```python
from app.modules.imports.domain.canonical_schema import validate_canonical

for item in result["products"]:
    canonical_doc = validate_canonical(item, schema_type="product")
    if canonical_doc.is_valid():
        # Item válido
        pass
    else:
        # Item con errores
        print(canonical_doc.errors)
```

### Paso 3: Obtener handler según doc_type (Fase C)
```python
from app.modules.imports.domain.handlers_router import get_handler

handler = get_handler(canonical_doc.doc_type)
if handler and handler.validate(canonical_doc):
    # Handler disponible y válido
    pass
```

### Paso 4: Promocionar a tabla destino (Fase C)
```python
promoted_id = handler.promote(canonical_doc, tenant_id)
# Inserta en tabla 'products' y retorna ID insertado
```

---

## 📝 Checklist de Fase C

### Implementación
- [ ] Extender canonical_schema.py
  - [ ] Agregar ProductCanonicalDocument
  - [ ] Agregar ExpenseCanonicalDocument
  - [ ] Agregar validadores
  
- [ ] Crear ProductHandler
  - [ ] Método validate()
  - [ ] Método promote()
  - [ ] Mapeo a tabla 'products'
  
- [ ] Crear ExpenseHandler
  - [ ] Método validate()
  - [ ] Método promote()
  - [ ] Mapeo a tabla 'expenses'
  
- [ ] Actualizar handlers_router.py
  - [ ] Registrar ProductHandler
  - [ ] Registrar ExpenseHandler
  
- [ ] Crear validadores específicos
  - [ ] validators_product.py
  - [ ] validators_expense.py
  - [ ] validators_by_country.py

### Testing
- [ ] Test ProductHandler
- [ ] Test ExpenseHandler
- [ ] Test validadores
- [ ] Test integración completa

### Documentación
- [ ] Actualizar README
- [ ] Documentar nuevos handlers
- [ ] Ejemplos de uso
- [ ] Troubleshooting

---

## 🔗 Integración con Sistema Actual

### Ubicación en flujo Celery
```python
# En task_import_file()
for import_item in import_batch.items:
    result = parser["handler"](file_path)  # Fase B
    
    for parsed_item in result["items"]:
        # Fase C comienza aquí
        canonical = validate_canonical(parsed_item)
        if canonical.is_valid():
            handler = get_handler(canonical.doc_type)
            promoted_id = handler.promote(canonical, tenant_id)
            # Guardar lineage
```

### Ubicación en modelos
```python
# ImportItem necesita:
- canonical_doc (JSON) - Documento validado
- status ('OK', 'ERROR_VALIDATION', etc.)
- errors (JSON) - Errores de validación

# ImportLineage necesita:
- promoted_to (str) - Tabla destino ('products', 'expenses', etc.)
- promoted_ref (str) - ID del documento en tabla destino
```

---

## 📖 Documentación de Referencia

### Para entender la arquitectura:
- IMPORTADOR_PLAN.md - Plan general
- CANONICAL_IMPLEMENTATION.md - Implementación canónica

### Para ver los parsers disponibles:
- FASE_B_NUEVOS_PARSERS.md - Parsers nuevos
- PARSER_REGISTRY.md - Referencia completa

### Para ejemplos:
- CANONICAL_USAGE.md - Uso de esquema canónico
- handlers_complete.py - Handlers existentes (referencia)

---

## 🚀 Primeros Pasos

### 1. Familiarizarse con código actual
```bash
# Revisar handlers existentes
cat app/modules/imports/domain/handlers.py

# Revisar schema canónico
cat app/modules/imports/domain/canonical_schema.py

# Revisar router existente
cat app/modules/imports/domain/handlers_router.py
```

### 2. Entender estructura de datos
```python
# Ejecutar parser y ver salida
from app.modules.imports.parsers import registry
parser = registry.get_parser("csv_products")
result = parser["handler"]("test_file.csv")
print(result)  # Ver estructura
```

### 3. Planificar extensiones
```
canonical_schema.py
├── Clase base CanonicalDocument
├── ProductCanonicalDocument (NUEVO)
└── ExpenseCanonicalDocument (NUEVO)

handlers_router.py
├── get_handler() existente
└── Agregar 'product' y 'expense' (NUEVO)

handlers.py
├── ProductHandler (NUEVO)
└── ExpenseHandler (NUEVO)
```

---

## ⚠️ Consideraciones Importantes

### Compatibilidad hacia atrás
- Los handlers actuales deben seguir funcionando
- No modificar doc_types existentes ('invoice', 'bank_tx')
- Agregar nuevos sin afectar existentes

### Validación
- Cada doc_type puede tener reglas distintas
- Considerar validadores por país/sector
- Mantener registro de errores de validación

### Rendimiento
- Validación antes de inserción
- Deduplicación según negocio
- Transacciones atómicas en promote()

---

## 📞 Próximos Pasos

1. **Revisar** documentación de Fase B
2. **Entender** estructura actual de handlers
3. **Diseñar** nuevos handlers para product y expense
4. **Implementar** validadores canónicos
5. **Crear** tests de integración
6. **Documentar** cambios

---

## 📚 Stack de Tecnología Usado

- **Validación**: Pydantic (models + validators)
- **Base de datos**: SQLAlchemy ORM
- **Task Queue**: Celery
- **Formato canónico**: JSON (SPEC-1)

---

## ✅ Checklist Pre-Implementación

- [x] Fase B completada
- [x] Parsers registrados y funcionando
- [x] Documentación de Fase B disponible
- [x] Ambiente de desarrollo listo
- [ ] Este documento leído completamente
- [ ] Equipo alineado en objetivos

---

**Una vez completadas las tareas de Fase C, estaremos listos para pasar a Fase D (IA Configurable).**

Para preguntas o dudas durante la implementación, consultar:
- DIAGNOSTICO_FASE_B.md
- CHECKLIST_FASE_B.md
- FASE_B_INDEX.md
