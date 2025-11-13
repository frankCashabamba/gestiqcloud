# Migración: Sistema de Nóminas RRHH

**ID**: 2025-11-03_201_hr_nominas  
**Fecha**: 2025-11-03  
**Autor**: GestiQCloud Team  

## Descripción

Sistema completo de gestión de nóminas con devengos, deducciones y conceptos salariales configurables. Compatible con España (IRPF, Seg. Social) y Ecuador (IR, IESS).

## Cambios Incluidos

### Tablas Creadas

1. **nominas**
   - Registro de nóminas mensuales por empleado
   - Devengos: salario_base, complementos, horas_extra, otros_devengos
   - Deducciones: seg_social, irpf, otras_deducciones
   - Totales calculados automáticamente
   - Estados: DRAFT, APPROVED, PAID, CANCELLED
   - Tipos: MENSUAL, EXTRA, FINIQUITO, ESPECIAL

2. **nomina_conceptos**
   - Conceptos individuales de devengos/deducciones
   - Tipos: DEVENGO, DEDUCCION
   - Códigos configurables (PLUS_TRANS, ANTICIPO, etc.)
   - Marca si computa para base de cotización

3. **nomina_plantillas**
   - Plantillas reutilizables de conceptos por empleado
   - Configuración en JSON
   - Permite generar nóminas automáticamente

### Tipos ENUM

- `nomina_status`: DRAFT, APPROVED, PAID, CANCELLED
- `nomina_tipo`: MENSUAL, EXTRA, FINIQUITO, ESPECIAL

### Características

✅ **RLS (Row Level Security)**: Aislamiento multi-tenant completo  
✅ **Constraints**: Validaciones de integridad (checks, FKs, unique)  
✅ **Índices**: Optimización para consultas por período, empleado, status  
✅ **Triggers**: Auto-actualización de updated_at  
✅ **Funciones**: Validación opcional de totales  
✅ **Auditoría**: Campos approved_by, approved_at, created_by  

### Integridad

- FK a `tenants` con CASCADE DELETE
- FK a `empleados` con RESTRICT (no se puede eliminar empleado con nóminas)
- UNIQUE constraint: Un empleado no puede tener dos nóminas del mismo tipo/período
- CHECK constraints: Validación de rangos (mes 1-12, año 2020-2100, importes >= 0)

## Dependencias

### Requiere

- Tabla `tenants` (existente)
- Tabla `empleados` (existente)
- Función `update_updated_at_column()` (existente)

### No requiere

- No tiene dependencias con otras tablas de nóminas (es autosuficiente)

## Cómo Usar

### 1. Aplicar Migración

```bash
# Automático (bootstrap)
python scripts/py/bootstrap_imports.py --dir ops/migrations

# Manual
psql -U postgres -d gestiqclouddb_dev -f ops/migrations/2025-11-03_201_hr_nominas/up.sql
```

### 2. Rollback

```bash
psql -U postgres -d gestiqclouddb_dev -f ops/migrations/2025-11-03_201_hr_nominas/down.sql
```

### 3. Verificación

```sql
-- Verificar tablas
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename LIKE 'nomina%';

-- Verificar RLS
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename LIKE 'nomina%';

-- Verificar tipos
SELECT typname FROM pg_type 
WHERE typname LIKE 'nomina%';
```

## Ejemplo de Uso

### Crear Nómina

```sql
-- Insertar nómina mensual
INSERT INTO nominas (
    tenant_id, numero, empleado_id,
    periodo_mes, periodo_ano, tipo,
    salario_base, complementos, horas_extra,
    total_devengado, seg_social, irpf,
    total_deducido, liquido_total,
    status
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    'NOM-2025-11-0001',
    '223e4567-e89b-12d3-a456-426614174001',
    11, 2025, 'MENSUAL',
    1500.00, 200.00, 100.00,
    1800.00, 114.30, 270.00,
    384.30, 1415.70,
    'DRAFT'
);
```

### Consultar Nóminas de un Empleado

```sql
SELECT 
    numero, periodo_mes, periodo_ano, tipo,
    total_devengado, total_deducido, liquido_total,
    status
FROM nominas
WHERE empleado_id = '223e4567-e89b-12d3-a456-426614174001'
ORDER BY periodo_ano DESC, periodo_mes DESC;
```

### Aprobar y Pagar Nómina

```sql
-- Aprobar
UPDATE nominas
SET status = 'APPROVED',
    approved_by = '323e4567-e89b-12d3-a456-426614174002',
    approved_at = NOW()
WHERE numero = 'NOM-2025-11-0001';

-- Pagar
UPDATE nominas
SET status = 'PAID',
    fecha_pago = '2025-11-30',
    metodo_pago = 'transferencia'
WHERE numero = 'NOM-2025-11-0001';
```

## Notas Técnicas

### Cálculo de Devengos

```
total_devengado = salario_base + complementos + horas_extra + otros_devengos
```

### Cálculo de Deducciones

```
España:
- Seg. Social: ~6.35% sobre base de cotización
- IRPF: Según tramos fiscales (19% - 45%)

Ecuador:
- IESS: 9.45% sobre base
- IR: Según tramos (0% - 15%)
```

### Cálculo de Líquido

```
liquido_total = total_devengado - total_deducido
```

### Base de Cotización

Solo se incluyen conceptos con `es_base = TRUE`

## Impacto

- **Performance**: Índices optimizados para consultas frecuentes
- **Seguridad**: RLS garantiza aislamiento multi-tenant
- **Escalabilidad**: Diseño preparado para millones de registros
- **Flexibilidad**: Conceptos configurables via JSON y tabla relacionada

## Testing

```bash
# Ejecutar tests unitarios
pytest apps/backend/app/tests/test_hr_nominas.py -v

# Verificar integridad
python scripts/verify_nominas_integrity.py
```

## Referencias

- Router: `apps/backend/app/routers/hr_complete.py`
- Schemas: `apps/backend/app/schemas/hr_nomina.py`
- Models: `apps/backend/app/models/hr/nomina.py`

## Changelog

- **2025-11-03**: Creación inicial del sistema de nóminas
