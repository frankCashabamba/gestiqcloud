# Migración 2025-10-27_400: Sistema IA + Incidencias + Alertas

## Objetivo

Crear la base para:
1. Sistema de incidencias con IA auto-resolución
2. Alertas automáticas de stock bajo
3. Notificaciones multi-canal (Email, WhatsApp, Telegram)

## Tablas Creadas

### 1. incidents
- Incidencias del sistema (errores, bugs, solicitudes)
- Auto-detección de errores
- Campo `ia_analysis` JSONB para análisis LLM
- Campo `ia_suggestion` TEXT para sugerencia de fix
- Estados: open, in_progress, resolved, auto_resolved

### 2. stock_alerts
- Alertas de inventario
- Tipos: stock_bajo, stock_agotado, caducidad_proxima
- Auto-creación vía trigger en stock_moves
- Notificaciones multi-canal

### 3. notification_channels
- Configuración de canales por tenant
- Email, WhatsApp, Telegram, Slack, Webhook
- Config JSONB (API keys, destinatarios, etc.)

### 4. notification_log
- Historial de notificaciones enviadas
- Estados: pending, sent, failed
- Trazabilidad completa

## Funciones SQL

### check_low_stock()
Detecta productos con `qty < reorder_point` y crea alertas automáticamente.

### trigger_check_low_stock_on_move()
Se ejecuta en cada movimiento de stock (AFTER INSERT/UPDATE en stock_moves).

## Características

- ✅ RLS habilitado en todas las tablas
- ✅ Índices optimizados
- ✅ Triggers automáticos
- ✅ Validaciones con CHECK
- ✅ Función detección stock bajo
- ✅ Trigger auto-creación alertas

## Verificación

```sql
-- Ver incidencias
SELECT * FROM incidents ORDER BY created_at DESC LIMIT 10;

-- Ver alertas stock
SELECT * FROM stock_alerts WHERE estado = 'active';

-- Verificar función
SELECT check_low_stock();

-- Ver canales notificación
SELECT * FROM notification_channels WHERE activo = TRUE;
```

## Próximos Pasos

1. Backend: Modelos SQLAlchemy
2. Backend: Routers incidents + alerts
3. Backend: Worker Celery notificaciones
4. Backend: IA analyzer (GPT-4/Claude)
5. Admin UI: Visor logs
6. Admin UI: Panel incidencias
7. Tenant UI: Configurar alertas
