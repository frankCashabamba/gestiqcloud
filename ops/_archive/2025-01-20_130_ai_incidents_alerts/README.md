# Migración: Sistema de Incidencias y Alertas IA

## Descripción

Crea las tablas necesarias para el sistema de incidencias y alertas inteligentes:

- **incidents**: Registro de incidencias con análisis IA
- **stock_alerts**: Alertas de inventario (stock bajo, caducidad, etc.)
- **notification_channels**: Canales de notificación (email, WhatsApp, etc.)
- **notification_log**: Log de notificaciones enviadas
- **alert_acknowledgements**: Reconocimientos de alertas

## Tablas Creadas

### 1. incidents
Sistema de incidencias con soporte para análisis y recomendaciones IA.

**Campos clave**:
- `severity`: low, medium, high, critical
- `status`: open, investigating, resolved, closed
- `ia_analysis`: Análisis automático del incidente
- `ia_recommendation`: Recomendación automática

### 2. stock_alerts
Alertas automáticas de inventario.

**Tipos de alerta**:
- `low_stock`: Stock por debajo del mínimo
- `out_of_stock`: Sin stock
- `expiring`: Próximo a caducar
- `expired`: Caducado
- `overstock`: Stock excesivo

### 3. notification_channels
Configuración de canales de notificación por tenant.

**Tipos soportados**:
- email
- whatsapp
- telegram
- webhook
- sms

### 4. notification_log
Registro de todas las notificaciones enviadas.

**Estados**:
- pending: Pendiente de envío
- sent: Enviado exitosamente
- failed: Falló el envío
- bounced: Rebotado

## Políticas RLS

Todas las tablas tienen RLS habilitado con políticas de aislamiento por tenant usando `app.tenant_id`.

## Índices

Se crean índices optimizados para:
- Búsquedas por tenant + status
- Filtrado por tipo/severidad
- Ordenamiento por fecha
- Lookups por referencias

## Orden de Aplicación

Esta migración debe aplicarse **después de**:
- 2025-10-10_090_pos/ (tablas POS)
- Migración de tenants
- Migración de products
- Migración de warehouses

## Dependencias

- Requiere tabla `tenants` existente
- Requiere tabla `products` existente
- Requiere tabla `warehouses` existente (o crear stub si no existe)

## Verificación

```sql
-- Verificar tablas creadas
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('incidents', 'stock_alerts', 'notification_channels', 'notification_log')
ORDER BY tablename;

-- Verificar RLS habilitado
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('incidents', 'stock_alerts', 'notification_channels', 'notification_log');
```

## Notas

- Los modelos ya existen en `app/models/ai/incident.py`
- Esta migración hace el esquema consistente con los modelos
- Las alertas de stock se pueden generar automáticamente via triggers (futura mejora)
