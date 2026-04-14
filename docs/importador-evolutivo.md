# Importador Evolutivo

Última actualización: 2026-04-14

## Propósito

Este documento define la hoja de ruta evolutiva del importador a partir de la base actual ya estabilizada.

La idea no es seguir sumando reglas sueltas, sino convertir el importador en un sistema:

- estable
- medible
- versionado
- fácil de mantener
- deterministic-only por ahora
- mejorable por fases

## Base actual

La base sobre la que se evoluciona hoy es:

- OCR nativo como ruta principal para PDF e imagen
- ruta estructurada directa para Excel, CSV y XML
- clasificación nativa por familia documental
- IA desactivada por defecto en todo el flujo de importación
- promoción controlada de `INVOICE`, `RECEIPT`, `SALES`, `PAYROLL`, `BANK_STATEMENT`, `INVENTORY`, `COSTING` y `OTHER`
- tests reales por documentos representativos
- logs con trazabilidad por documento y por etapa

## Principios de evolución

1. No romper lo que ya funciona.
2. Toda mejora debe acabar en test.
3. Las reglas deben ser por familia documental, no por archivo.
4. Si una decisión no es segura, debe terminar en `REVIEW`.
5. La clasificación debe preferir evidencia real antes que inferencias amplias.
6. Cada ajuste importante debe poder revertirse.

## Fase 1. Estabilización

### Objetivo

Congelar una baseline fiable para seguir evolucionando sin degradación silenciosa.

### Acciones

- Mantener la ruta nativa como comportamiento principal.
- Evitar reactivar fallbacks externos sin una razón medible.
- Consolidar las reglas de clasificación ya validadas.
- Registrar casos borde como regresiones.
- Separar claramente tipos documentales cercanos:
  - factura de proveedor
  - recibo/ticket
  - resumen de ventas
  - nómina
  - extracto bancario

### Criterio de salida

- Los documentos representativos se clasifican de forma consistente.
- Los casos ambiguos terminan en `REVIEW` antes que en un tipo incorrecto.
- Los cambios de la fase tienen tests que los cubren.

### Estado actual

- Hecho parcial: base dorada inicial creada con documentos reales representativos.
- Cobertura actual: factura de proveedor, ventas/resumen, nómina, recibo/ticket y factura por imagen.
- La cobertura de imagen puede ejecutarse de forma opt-in para no penalizar la suite por defecto.

## Fase 2. Robustez

### Objetivo

Hacer que el importador soporte variaciones reales de calidad, formato y redacción sin degradar la clasificación.

### Acciones

- Construir un set dorado de documentos por familia.
- Medir por documento:
  - tipo detectado
  - campos clave
  - `line_items`
  - `total_amount`
  - `issue_date`
  - `vendor`
  - `requires_review`
- Ajustar reglas solo cuando haya evidencia suficiente.
- Reducir dependencias en heurísticas demasiado generales.
- Reforzar la diferenciación entre:
  - `INVOICE` y `RECEIPT`
  - `RECEIPT` y `SALES`
  - `OTHER` y tipos con evidencia parcial

### Criterio de salida

- Cada familia tiene cobertura mínima con casos reales.
- Los errores recurrentes dejan de corregirse manualmente y pasan a ser tests.
- La tasa de falsos positivos baja de forma medible.

## Fase 3. Calidad de producción

### Objetivo

Que el importador sea operable en producción con trazabilidad y control de calidad.

### Acciones

- Medir calidad por capa:
  - OCR
  - clasificación
  - extracción
  - routing
  - persistencia
- Definir umbrales de confianza por familia documental.
- Mantener `REVIEW` como salida segura cuando falte evidencia.
- Añadir observabilidad útil:
  - latencia por etapa
  - tasa de reintentos
  - tasa de revisión
  - tasa de acierto por tipo
- Versionar reglas y cambios de comportamiento.

### Criterio de salida

- El sistema puede operarse con métricas claras.
- Los cambios tienen impacto visible y medible.
- La calidad deja de depender de revisión manual constante.

## Qué no hacer

- No seguir agregando excepciones por nombre de archivo.
- No meter heurísticas globales que rompan familias ya estables.
- No forzar un tipo documental si la evidencia es débil.
- No introducir cambios grandes sin cobertura de prueba.
- No mezclar en un solo cambio:
  - clasificación
  - OCR
  - routing
  - UI

## Métricas mínimas

- porcentaje de documentos clasificados correctamente por familia
- porcentaje de documentos enviados a `REVIEW`
- latencia media y p95 por ruta
- tasa de extracción completa por tipo
- número de regresiones abiertas por release

## Orden recomendado de trabajo

1. Congelar baseline actual.
2. Crear set dorado.
3. Ejecutar lote de validación.
4. Clasificar fallos por familia.
5. Ajustar una sola familia por iteración.
6. Convertir cada mejora en regresión automatizada.
7. Repetir el ciclo.

## Relación con otros documentos

- [Importador Checklist](./importador-checklist.md)
- [Plan Maestro de Desarrollo](./PLAN_MAESTRO_DESARROLLO.md)
- [Índice de módulos backend](./modules-index.md)

## Resultado esperado

El importador debe evolucionar hacia un sistema donde:

- lo estable se conserva
- lo ambiguo se revisa
- lo nuevo se valida
- lo corregido queda cubierto por tests
