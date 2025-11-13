# Módulo Importador Universal

**Un solo módulo de importación para todas las plantillas y tipos de datos.**

## 🎯 Objetivo

Proporcionar un sistema de importación **universal y configurable** que sirva para:
- ✅ Todas las plantillas (todoa100, panaderia, taller, etc.)
- ✅ Todos los tipos de datos (productos, clientes, inventario, etc.)
- ✅ Todos los tenants (multi-tenant con RLS automático)

## 📁 Estructura

```
importador/
├── config/
│   └── entityTypes.ts          # ⭐ Configuración de tipos de entidades
├── components/
│   ├── ImportadorLayout.tsx    # Layout del módulo
│   ├── ColumnMapper.tsx        # Mapeo de columnas
│   └── ...
├── services/
│   ├── importsApi.ts           # API del backend /v1/imports/*
│   └── autoMapeoColumnas.ts    # Auto-mapeo inteligente
├── utils/
│   ├── aliasCampos.ts          # Aliases de columnas
│   └── detectarTipoDocumento.ts
├── ImportadorExcel.tsx         # Componente principal
├── Panel.tsx                   # Vista de batches
└── manifest.ts                 # Registro del módulo
```

## 🚀 Uso

### 1. Desde cualquier plantilla

```tsx
import { Link } from 'react-router-dom'

// Botón para ir al importador
<Link to="/importador" className="btn btn-primary">
  📤 Importar datos
</Link>
```

### 2. Configurar tipos de datos disponibles

Edita `config/entityTypes.ts`:

```typescript
export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = {
  productos: {
    type: 'productos',
    label: 'Productos',
    icon: '📦',
    endpoint: '/v1/imports/batches',
    checkDuplicates: true,
    duplicateKeys: ['sku'],
    fields: [
      {
        field: 'nombre',
        aliases: ['nombre', 'producto', 'name'],
        required: true,
        type: 'string',
      },
      // ... más campos
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'taller'], // ⭐ Configura qué plantillas pueden usar este tipo
  }
}
```

### 3. El usuario selecciona el tipo y sube el Excel

El sistema:
1. ✅ Detecta automáticamente las columnas
2. ✅ Mapea usando aliases configurados
3. ✅ Valida datos según la configuración
4. ✅ Detecta duplicados si está configurado
5. ✅ Crea batch multi-tenant (automático)
6. ✅ Permite correcciones antes de guardar

## 📋 Tipos de Datos Soportados

| Tipo | Plantillas | Backend | Duplicados |
|------|-----------|---------|------------|
| 📦 Productos | todoa100, panaderia, taller | ✅ | sku, codigo_barras |
| 👥 Clientes | todoa100, panaderia, taller | ✅ | email, documento |
| 🏭 Proveedores | todoa100, panaderia, taller | ✅ | documento |
| 📊 Inventario | todoa100, panaderia | ✅ | - |
| 💰 Ventas | todoa100, panaderia, taller | ✅ | - |
| 🛒 Compras | panaderia | ✅ | - |
| 🧾 Facturas | todoa100, panaderia, taller | ✅ | - |
| 💸 Gastos | default | ✅ | - |
| 👔 Empleados | default | ✅ | documento, email |

## 🔧 Agregar un Nuevo Tipo de Datos

1. **Edita `config/entityTypes.ts`**:

```typescript
export type EntityType =
  | 'productos'
  | 'mi_nuevo_tipo' // ⭐ Agregar aquí

export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = {
  // ... existentes

  mi_nuevo_tipo: {
    type: 'mi_nuevo_tipo',
    label: 'Mi Tipo',
    icon: '🆕',
    endpoint: '/v1/imports/batches',
    checkDuplicates: false,
    fields: [
      {
        field: 'campo1',
        aliases: ['campo1', 'field1', 'c1'],
        required: true,
        type: 'string',
        description: 'Descripción del campo',
      },
    ],
    allowedTemplates: ['todoa100'], // Qué plantillas pueden usarlo
  },
}
```

2. **Listo**. El frontend detectará automáticamente el nuevo tipo.

## 🎨 Personalización por Plantilla

Cada plantilla puede:

```tsx
// En todoa100.tsx o cualquier plantilla
import { getEntityTypesForTemplate } from '../modules/importador/config/entityTypes'

const tiposDisponibles = getEntityTypesForTemplate('todoa100')
// Retorna: ['productos', 'clientes', 'inventario', ...]
```

## 📤 Formato de Excel Soportado

El usuario puede subir Excel con columnas en **cualquier idioma** gracias a los aliases:

### Ejemplo: Productos

| nombre | sku | precio | stock | categoria |
|--------|-----|--------|-------|-----------|
| Coca Cola 2L | COCA-2L | 2.50 | 100 | Bebidas |
| Pan integral | PAN-INT | 1.20 | 50 | Panadería |

También acepta:
- **Inglés**: `name`, `code`, `price`, `quantity`, `category`
- **Otros**: `producto`, `código`, `existencias`, etc.

El sistema **mapea automáticamente** según la configuración de aliases.

## 🔒 Multi-Tenant Automático

El backend (`/v1/imports/*`) ya implementa RLS:
- ✅ Filtra por `tenant_id` automáticamente
- ✅ Cada tenant solo ve sus propios batches
- ✅ No requiere configuración adicional

## 🧪 Testing

```bash
# Frontend
npm run test -- importador

# Backend
pytest apps/backend/app/tests/test_imports.py
```

## 📝 Notas de Implementación

1. **NO crear ExcelImporter por plantilla**: Usar este módulo universal
2. **Configurar solo los tipos permitidos**: En `allowedTemplates`
3. **El backend ya está preparado**: Endpoints `/v1/imports/*` operativos
4. **Validación en 2 capas**: Frontend (config) + Backend (Pydantic)

## 🚧 Próximos Pasos (M2-M3)

- [ ] Importación desde fotos (OCR ya implementado)
- [ ] Plantillas descargables por tipo
- [ ] Historial de importaciones
- [ ] Rollback de batches
- [ ] Webhooks post-importación
- [ ] ElectricSQL sync offline

---

**Autor**: GestiQCloud Team
**Versión**: 1.0.0
**Última actualización**: Enero 2025
