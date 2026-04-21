# Guía de Refactorización - Reducción de Código Duplicado

Este documento describe las nuevas utilidades y patrones implementados para reducir la duplicación de código en GestiQCloud.

## 📋 Tabla de Contenidos

1. [Backend - Modelos Base](#backend-modelos-base)
2. [Backend - Decorators de Validación](#backend-decorators-de-validación)
3. [Backend - Generador de Schemas](#backend-generador-de-schemas)
4. [Frontend - Tipos Centralizados](#frontend-tipos-centralizados)
5. [Frontend - Hooks Reutilizables](#frontend-hooks-reutilizables)
6. [Ejemplos de Uso](#ejemplos-de-uso)
7. [Migración Gradual](#migración-gradual)

---

## Backend - Modelos Base

### BaseCatalogModel

Clase base para entidades catálogo con campos comunes:

```python
from app.models.base import BaseCatalogModel

class BusinessType(BaseCatalogModel):
    __tablename__ = "business_types"
    __table_args__ = {"extend_existing": True}
    # No need to define id, tenant_id, code, name, description,
    # is_active, created_at, updated_at - inherited!
```

**Campos heredados:**
- `id: UUID` - Primary key
- `tenant_id: UUID` - Multi-tenancy
- `code: str | None` - Código externo
- `name: str` - Nombre requerido
- `description: str | None` - Descripción opcional
- `is_active: bool` - Estado activo
- `created_at: datetime` - Timestamp creación
- `updated_at: datetime` - Timestamp actualización

**Propiedades adicionales:**
- `active` - Alias backward compatible para `is_active`

### BaseCatalogModelWithoutTenant

Similar a `BaseCatalogModel` pero sin `tenant_id` para catáglobales del sistema:

```python
class Language(BaseCatalogModelWithoutTenant):
    __tablename__ = "languages"
    # Para catálogos del sistema, override id si es necesario
    id: Mapped[int] = mapped_column(primary_key=True)
```

---

## Backend - Decorators de Validación

### validate_uuid()

Valida y convierte string a UUID:

```python
from app.decorators.validation import validate_uuid

@router.put("/{business_type_id}")
def update_business_type(business_type_id: str):
    uuid = validate_uuid(business_type_id, "business_type_id")
    # uuid es ahora un objeto UUID válido
```

### tenant_required

Extrae y valida tenant_id del request:

```python
from app.decorators.validation import tenant_required

@router.get("/business-types")
@tenant_required
def list_business_types(
    request: Request,
    tenant_id: str = None  # Auto-agregado por el decorator
):
    # tenant_id está disponible y validado
```

### validate_resource_exists

Valida que un recurso existe antes de ejecutar el endpoint:

```python
from app.decorators.validation import validate_resource_exists

def get_business_type(db: Session, tenant_id: str, business_type_id: str):
    return db.query(BusinessType).filter(
        BusinessType.tenant_id == tenant_id,
        BusinessType.id == business_type_id
    ).first()

@router.get("/{business_type_id}")
@tenant_required
@validate_resource_exists(get_business_type, "Business Type")
def get_business_type(
    validated_business_type: BusinessType = None  # Auto-agregado
):
    return validated_business_type
```

### handle_not_found

Manejo estandarizado de errores 404:

```python
from app.decorators.validation import handle_not_found

@router.delete("/{business_type_id}")
@handle_not_found("Business Type")
def delete_business_type(business_type_id: str):
    # Si se lanza ValueError con "not found", se convierte a HTTP 404
```

### validate_pagination_params

Valida y sanea parámetros de paginación:

```python
from app.decorators.validation import validate_pagination_params

@router.get("/")
@validate_pagination_params
def list_items(page: int = 1, per_page: int = 20):
    # page ≥ 1, per_page entre 1 y 1000
```

---

## Backend - Generador de Schemas

### create_catalog_schemas()

Genera automáticamente schemas Base/Create/Update/Response:

```python
from app.utils.schema_generator import create_catalog_schemas

# Genera todos los schemas para BusinessType
schemas = create_catalog_schemas("BusinessType")
BusinessTypeBase = schemas["Base"]
BusinessTypeCreate = schemas["Create"]
BusinessTypeUpdate = schemas["Update"]
BusinessTypeResponse = schemas["Response"]
```

**Campos generados automáticamente:**
- **Base**: name, code, description, is_active, tenant_id (opcional)
- **Create**: Hereda de Base
- **Update**: Todos los campos opcionales (excepto tenant_id)
- **Response**: Base + id + timestamps

### Con campos adicionales:

```python
schemas = create_catalog_schemas(
    "SectorTemplate",
    extra_fields={
        "template_config": (Optional[Dict[str, Any]], Field(default_factory=dict)),
        "config_version": (Optional[int], Field(None)),
    }
)
```

### Schemas predefinidos:

```python
from app.utils.schema_generator import get_catalog_schemas

# Usa schemas predefinidos para catálogos comunes
schemas = get_catalog_schemas("BusinessType")
```

---

## Frontend - Tipos Centralizados

### Importar desde @packages/api-types

```typescript
import type {
  BusinessType,
  BusinessCategory,
  CatalogCreateRequest,
  CatalogUpdateRequest,
  CatalogFilters,
  PaginatedResponse
} from '@packages/api-types'
```

### Tipos disponibles

**BaseCatalog:**
```typescript
interface BaseCatalog {
  id: UUID
  tenant_id?: UUID
  code?: string
  name: string
  description?: string
  is_active: boolean
  created_at: Timestamp
  updated_at: Timestamp
}
```

**Tipos específicos:**
- `BusinessType extends BaseCatalog`
- `BusinessCategory extends BaseCatalog`
- `SectorTemplate extends BaseCatalog`
- `CatalogLanguage` (sin tenant_id)
- `CatalogCurrency` (sin tenant_id)
- `CatalogCountry` (sin tenant_id)

---

## Frontend - Hooks Reutilizables

### useCatalogCRUD

Hook completo para gestión de catálogos:

```typescript
import { useCatalogCRUD } from '@packages/ui-hooks'
import { listBusinessTypes, getBusinessType, createBusinessType, updateBusinessType, deleteBusinessType } from '../services/catalogs'

function BusinessTypesPage() {
  const catalog = useCatalogCRUD({
    list: listBusinessTypes,
    get: getBusinessType,
    create: createBusinessType,
    update: updateBusinessType,
    delete: deleteBusinessType,
    tenantId: 'tenant-123',
    initialFilters: { is_active: true }
  })

  return (
    <div>
      {catalog.loading && <div>Loading...</div>}
      {catalog.error && <div>Error: {catalog.error}</div>}

      <button onClick={() => catalog.loadItems()}>Refresh</button>
      <button onClick={() => catalog.createItem({ name: 'New Type' })}>
        Create
      </button>

      <ul>
        {catalog.items.map(item => (
          <li key={item.id}>
            {item.name}
            <button onClick={() => catalog.loadItem(item.id)}>Edit</button>
            <button onClick={() => catalog.deleteItem(item.id)}>Delete</button>
          </li>
        ))}
      </ul>

      <PaginationControls pagination={catalog.pagination} />
    </div>
  )
}
```

**Funcionalidades incluidas:**
- Listado con paginación y filtros
- Creación, lectura, actualización, eliminación
- Estados de loading individuales
- Manejo automático de errores
- Selección de items
- Refresco automático

---

## Ejemplos de Uso

### Backend: Endpoint completo

```python
# app/examples/catalog_endpoints.py
from app.decorators.validation import (
    tenant_required, validate_pagination_params,
    validate_resource_exists, handle_not_found
)
from app.utils.schema_generator import create_catalog_schemas

# Generar schemas automáticamente
schemas = create_catalog_schemas("BusinessType")
BusinessTypeCreate = schemas["Create"]
BusinessTypeResponse = schemas["Response"]

@router.get("/")
@tenant_required
@validate_pagination_params
def list_business_types(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Auto por tenant_required
    page: int = 1,
    per_page: int = 20
):
    # Sin validación manual - decorators la hacen!
    query = db.query(BusinessType).filter(BusinessType.tenant_id == tenant_id)

    total = query.count()
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }
```

### Frontend: Servicio centralizado

```typescript
// services/catalogs.ts
import { createCatalogService } from './catalogs'

// Crear servicio para cualquier catálogo
const businessTypeService = createCatalogService<BusinessType>('business-types')

// Usar en componentes
function BusinessTypesComponent() {
  const [items, setItems] = useState<BusinessType[]>([])

  useEffect(() => {
    businessTypeService.list(tenantId, { page: 1, per_page: 20 })
      .then(response => setItems(response.items))
  }, [])

  return (
    <button onClick={() => businessTypeService.create(tenantId, { name: 'New' })}>
      Create
    </button>
  )
}
```

---

## Migración Gradual

### Paso 1: Identificar modelos catálogo

Buscar modelos con patrones repetitivos:
```python
# Modelos que heredan de BaseCatalogModel:
class BusinessType(BaseCatalogModel):  # ✅ Ya migrado
class BusinessCategory(BaseCatalogModel):  # ✅ Ya migrado
class SectorTemplate(BaseCatalogModel):  # ✅ Ya migrado

# Modelos por migrar:
class Language(Base):  # ❌ Migrar a BaseCatalogModelWithoutTenant
class Currency(Base):  # ❌ Migrar a BaseCatalogModelWithoutTenant
```

### Paso 2: Migrar schemas manuales

Reemplazar schemas manuales con generados:

```python
# ANTES (manual):
class BusinessTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str | None = Field(None, max_length=50)
    # ... 20+ líneas más

# DESPUÉS (generado):
from app.utils.schema_generator import get_catalog_schemas
schemas = get_catalog_schemas("BusinessType")
BusinessTypeBase = schemas["Base"]  # 1 línea!
```

### Paso 3: Aplicar decorators en endpoints

Reemplazar validación manual con decorators:

```python
# ANTES:
@router.get("/{business_type_id}")
def get_business_type(business_type_id: str, request: Request):
    try:
        uuid = UUID(business_type_id)
    except ValueError:
        raise HTTPException(400, "Invalid ID")

    claims = getattr(request.state, "access_claims", {})
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(400, "Tenant not found")

    # ... lógica del endpoint

# DESPUÉS:
@router.get("/{business_type_id}")
@tenant_required
@validate_resource_exists(get_business_type, "Business Type")
def get_business_type(
    validated_business_type: BusinessType = None
):
    return validated_business_type
```

### Paso 4: Actualizar frontend

Reemplazar tipos duplicados con centralizados:

```typescript
// ANTES (duplicado en admin y tenant):
interface BusinessType {
  id: string
  name: string
  // ... definición completa
}

// DESPUÉS (centralizado):
import type { BusinessType } from '@packages/api-types'
```

---

## 📊 Impacto del Refactor

### Antes del Refactor

**Backend:**
- ~150 líneas por modelo catálogo (campos repetitivos)
- ~50 líneas por schema (Base/Create/Update/Response)
- ~20 líneas por endpoint (validaciones repetitivas)

**Frontend:**
- ~30 líneas por tipo (duplicado entre admin/tenant)
- ~100 líneas por servicio CRUD (patrones repetitivos)
- ~200 líneas por componente (manejo de estado repetitivo)

### Después del Refactor

**Backend:**
- ~5 líneas por modelo (herencia de BaseCatalogModel)
- ~3 líneas por schema (generación automática)
- ~5 líneas por endpoint (decorators)

**Frontend:**
- ~1 línea por tipo (import centralizado)
- ~20 líneas por servicio (servicio genérico)
- ~50 líneas por componente (useCatalogCRUD)

### Reducción Total

- **Backend**: ~70% menos código duplicado
- **Frontend**: ~80% menos código duplicado
- **Mantenimiento**: Cambios en un solo lugar afectan a todos
- **Consistencia**: Validaciones y tipos consistentes

---

## 🔧 Herramientas Creadas

| Archivo | Propósito | Uso |
|---------|-----------|------|
| `app/models/base.py` | Modelos base | Herencia para modelos catálogo |
| `app/decorators/validation.py` | Decoradores de validación | Reducir validación manual |
| `app/utils/schema_generator.py` | Generador de schemas | Creación automática de schemas |
| `packages/api-types/src/catalogs.ts` | Tipos centralizados | Compartir tipos entre frontends |
| `packages/ui-hooks/src/useCatalogCRUD.ts` | Hook CRUD | Gestión completa de catálogos |
| `app/examples/catalog_endpoints.py` | Ejemplos de uso | Patrones a seguir |
| `app/schemas/generated/hr_catalogs.py` | Ejemplo schemas | Generación automática |

---

## 🚀 Próximos Pasos

1. **Extender a más modelos**: Migrar todos los modelos catálogo restantes
2. **Estandarizar endpoints**: Aplicar decorators en todos los endpoints catálogo
3. **Adoptar en frontend**: Reemplazar tipos duplicados en todos los componentes
4. **Automatizar migración**: Crear script para identificar y migrar patrones duplicados
5. **Testing**: Asegurar que todo funcione correctamente después del refactor

---

## 📝 Notas Importantes

- **Backward Compatibility**: Todos los cambios mantienen compatibilidad con código existente
- **Gradual**: Puede implementarse incrementalmente sin afectar funcionalidad
- **Testing**: Cada cambio debe ir acompañado de tests adecuados
- **Documentación**: Actualizar documentación de APIs y componentes

---

## 🤝 Contribución

Para añadir nuevos catálogos:

1. **Backend**: Crear modelo heredando de `BaseCatalogModel` o `BaseCatalogModelWithoutTenant`
2. **Schemas**: Usar `create_catalog_schemas()` para generar automáticamente
3. **Endpoints**: Aplicar decorators de validación
4. **Frontend**: Añadir tipo a `@packages/api-types/src/catalogs.ts`
5. **Servicios**: Usar `createCatalogService()` para operaciones CRUD

Este patrón asegura consistencia y reduce drásticamente la duplicación de código.
