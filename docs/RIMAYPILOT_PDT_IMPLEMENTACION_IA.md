# RimayPilot - PDT de Implementacion IA

## Objetivo

Definir el plan de trabajo pendiente para convertir `RimayPilot` en la capa de IA transversal del sistema, reutilizando lo ya construido y evitando duplicidad de codigo o flujos.

Este documento asume tres reglas:

1. No se renombra la base tecnica interna `copilot` por compatibilidad.
2. No se toca `importador` como flujo funcional; solo se permiten mejoras incrementales y no disruptivas.
3. Toda accion de escritura asistida por IA debe ser estructurada, auditable y aprobable.

## Alcance

Incluye:

- chat y analitica asistida,
- optimizacion operativa por modulo,
- acciones asistidas con confirmacion,
- agentes de backoffice y procesos en segundo plano,
- observabilidad, seguridad y gobierno IA.

No incluye:

- autonomia total sobre pagos, fiscalidad, stock real, nomina o permisos,
- reescritura del importador,
- duplicar servicios IA ya existentes.

## Base Ya Implementada

La base actual ya es suficiente para escalar sin rehacer arquitectura:

- proveedores IA con fallback y health check en [factory.py](/C:/gestiqcloud/apps/backend/app/services/ai/factory.py) y [startup.py](/C:/gestiqcloud/apps/backend/app/services/ai/startup.py),
- servicio comun IA en [service.py](/C:/gestiqcloud/apps/backend/app/services/ai/service.py),
- metricas y logging IA en [logging.py](/C:/gestiqcloud/apps/backend/app/services/ai/logging.py),
- workers IA en [ai_tasks.py](/C:/gestiqcloud/apps/backend/app/workers/ai_tasks.py),
- catalogo central de RimayPilot en [catalog.py](/C:/gestiqcloud/apps/backend/app/modules/copilot/catalog.py),
- resolucion de contexto por modulo en [context_builder.py](/C:/gestiqcloud/apps/backend/app/modules/copilot/context_builder.py),
- API tenant de RimayPilot en [tenant.py](/C:/gestiqcloud/apps/backend/app/modules/copilot/interface/http/tenant.py),
- dashboard y widget frontend en [Dashboard.tsx](/C:/gestiqcloud/apps/tenant/src/modules/copilot/Dashboard.tsx) y [CopilotChatWidget.tsx](/C:/gestiqcloud/apps/tenant/src/components/CopilotChatWidget.tsx),
- optimizacion IA de recetas en [recipe_optimizer.py](/C:/gestiqcloud/apps/backend/app/services/recipe_optimizer.py) y [RecetaDetail.tsx](/C:/gestiqcloud/apps/tenant/src/modules/productions/RecetaDetail.tsx).

## Restriccion Fija: Importador

`Importador` es una pieza estrategica y no debe reescribirse ni recolgarse de nuevos flujos IA.

Politica para `importador`:

- mantener endpoints, UX y pipeline actuales,
- no cambiar contratos ni decisiones nucleares de extraccion/clasificacion,
- solo admitir mejoras de precision, observabilidad, retries, fallback, scoring y aprendizaje por correccion,
- cualquier mejora debe ser incremental y medible.

Fuera de alcance en esta fase:

- rediseño de OCR,
- sustitucion del pipeline actual,
- mover importador al chat o a acciones genericas de RimayPilot.

## Principios de Arquitectura

1. Un unico punto de entrada IA.
   Todo debe apoyarse en `AIService` y `AIProviderFactory`.

2. Un unico catalogo funcional.
   Los temas, acciones y modulos deben salir del catalogo central, no de strings sueltos.

3. Contexto por modulo.
   Cada modulo entrega contexto controlado, reducido y sin PII innecesaria.

4. Escritura estructurada.
   La IA no devuelve "haz X" en texto libre; devuelve payloads aplicables o borradores.

5. Confirmacion humana.
   Toda accion con impacto contable, inventario, fiscal, permisos o dinero requiere aprobacion.

6. Auditoria completa.
   Cada ejecucion debe guardar: `tenant`, `modulo`, `topic/action`, `provider`, `confidence`, `cost`, `latency`, `resultado`, `usuario`, `aprobado_por`.

7. Feature flags.
   Todo write flow nuevo debe quedar detras de flags similares a [service.py](/C:/gestiqcloud/apps/backend/app/modules/feature_flags/service.py).

## Modelo Operativo IA

### Nivel 1 - Lectura y analisis automatico

Casos:

- resumenes ejecutivos,
- analisis de metricas,
- deteccion de anomalias,
- explicacion de KPI,
- priorizacion de incidencias,
- forecast y alertas.

Riesgo: bajo.

### Nivel 2 - Asistencia con confirmacion

Casos:

- borradores de pedido,
- borradores de factura,
- sugerencias de reorden,
- propuestas de conciliacion,
- optimizacion de recetas,
- propuestas de precio o margen,
- recomendaciones CRM.

Riesgo: medio.

### Nivel 3 - Ejecucion restringida

Casos:

- aplicar propuestas ya validadas,
- lanzar tareas de background,
- crear registros en estado borrador,
- disparar notificaciones internas.

Riesgo: medio/alto. Requiere guardrails.

### Nivel 4 - Prohibido autonomo

No se automatiza sin aprobacion:

- pagos y devoluciones,
- asientos contables definitivos,
- envios fiscales,
- ajustes reales de inventario,
- cierre de nomina,
- permisos y accesos.

## PDT por Fases

## Fase 1 - Consolidacion de RimayPilot

Objetivo: cerrar la base comun y eliminar puntos sueltos.

Pendientes:

- consumir `GET /ai/catalog` desde cualquier pantalla o launcher que aun use tarjetas hardcodeadas,
- unificar todos los accesos frontend a los mismos contratos de `services.ts`,
- exponer mejor las feature flags IA en administracion,
- añadir una pantalla simple de estado de proveedores usando [ai_health.py](/C:/gestiqcloud/apps/backend/app/routers/ai_health.py),
- documentar variables de entorno y politica de fallback.

Aceptacion:

- no hay listas duplicadas de topics/actions,
- todos los modulos IA visibles salen del catalogo,
- el usuario puede saber si IA esta disponible o degradada.

## Fase 2 - Cobertura de Contexto por Modulo

Objetivo: que RimayPilot entienda todo el sistema, no solo algunas areas.

Modulos ya cubiertos:

- `pos`
- `inventory`
- `purchases`
- `sales`
- `finance`
- `manufacturing`
- `expenses`
- `hr`
- `products`
- `crm`
- `customers`
- `suppliers`
- `accounting`
- `invoicing`
- `einvoicing`
- `reconciliation`
- `reports`
- `notifications`
- `settings`
- `users`

Pendientes reales:

- revisar calidad del contexto, no solo cobertura,
- definir payloads maximos por modulo para no inflar prompts,
- introducir resumenes precomputados donde hoy se mandan datos demasiado crudos,
- marcar mejor datos sensibles para exclusiones o mascara.

Aceptacion:

- cada modulo relevante tiene contexto util, acotado y comprobable,
- tests de contexto por modulo cubren llaves y estructura minima.

## Fase 3 - Acciones Asistidas de Alto ROI

Objetivo: pasar de "consultar" a "preparar trabajo real".

### Compras

Implementar:

- sugerencia de orden de compra,
- recomendacion de proveedor segun precio/plazo/incidencias,
- deteccion de subida anomala de coste,
- recomendacion de consolidacion de pedidos.

Formato:

- crear siempre borrador,
- incluir razon, impacto esperado y confianza,
- nunca confirmar compra automaticamente.

### Inventario

Implementar:

- sugerencia de reorden,
- priorizacion de conteos,
- riesgo de rotura,
- riesgo de caducidad,
- deteccion de movimientos anomalos.

Guardrail:

- no hacer ajustes reales de stock desde IA.

### CRM y Clientes

Implementar:

- scoring de oportunidades,
- siguiente mejor accion,
- borradores de seguimiento,
- deteccion de clientes dormidos o en fuga,
- resumen ejecutivo por cliente.

### Reconciliacion y Finanzas

Implementar:

- matching sugerido con explicacion,
- priorizacion de diferencias,
- forecast de caja,
- deteccion de tensiones de liquidez,
- resumen diario de cobros y pagos.

Guardrail:

- no conciliar definitivamente sin aprobacion.

### Ventas y POS

Implementar:

- forecast por dia/hora,
- explicacion de cambios de ticket medio,
- deteccion de anomalias,
- sugerencia de combos o upsell,
- resumen automatico de cierre de caja.

### Produccion

Implementar:

- planificacion de lotes sugerida,
- alertas de merma,
- comparativa receta teorica vs consumo real,
- ranking de recetas con deterioro de margen.

Estado actual:

- ya existe optimizacion de recetas.

### Gastos y Contabilidad

Implementar:

- clasificacion sugerida de gasto,
- propuesta de centro de coste,
- resumen de desvio presupuestario,
- propuesta de asiento en borrador.

Guardrail:

- nunca contabilizacion final automatica.

## Fase 4 - Centro de Alertas Inteligentes

Objetivo: que el usuario no tenga que entrar modulo por modulo para detectar problemas.

Implementar:

- bandeja unica de alertas IA,
- agrupacion por severidad e impacto economico,
- explicacion corta y accion recomendada,
- resumen diario y semanal por tenant,
- trazabilidad de alerta resuelta, ignorada o convertida en tarea.

Fuente de datos:

- ventas,
- stock,
- compras,
- produccion,
- finanzas,
- soporte,
- notificaciones.

## Fase 5 - Agentes de Backoffice

Objetivo: mover trabajo repetitivo a procesos asincronos.

Implementar:

- agente de resumen diario ejecutivo,
- agente de vigilancia de anomalias,
- agente de preparacion de cierres y pendientes,
- agente de revision de incidencias/soporte,
- agente de seguimiento comercial.

Regla:

- los agentes trabajan sobre colas y generan propuestas o alertas,
- no ejecutan acciones sensibles por su cuenta.

## Fase 6 - Aprendizaje Operativo

Objetivo: que el sistema mejore con las correcciones reales.

Implementar:

- feedback explicito de usuario: util/no util,
- captura de correcciones aplicadas a borradores,
- scoring por tipo de accion,
- ajuste de prompts y reglas segun tasa de aceptacion,
- dataset interno de ejemplos validados por modulo.

No hacer:

- fine-tuning improvisado,
- aprendizaje opaco sin trazabilidad.

## Backlog por Modulo

| Modulo | Estado actual | Siguiente entrega | Riesgo |
| --- | --- | --- | --- |
| RimayPilot core | Base operativa | health UI, flags, auditoria visible | Medio |
| Produccion | Optimizacion de recetas lista | lotes, merma, deriva de coste | Medio |
| Inventario | Contexto y consultas | reorden, caducidad, anomalias | Medio |
| Compras | Contexto y consultas | orden sugerida y proveedor recomendado | Medio |
| CRM | Contexto y consultas | scoring y siguiente accion | Bajo |
| Reconciliacion | Contexto y consultas | matching sugerido y resumen de diferencias | Alto |
| Finanzas | Contexto y consultas | forecast y alertas de liquidez | Medio |
| Ventas/POS | Contexto y consultas | forecast y anomalias operativas | Bajo |
| Gastos | Contexto basico | clasificacion y centro de coste sugeridos | Medio |
| Contabilidad | Contexto basico | asientos borrador y resumen de desviaciones | Alto |
| Notificaciones | Contexto basico | bandeja IA unificada | Bajo |
| Soporte | IA ya presente | priorizacion y plantillas de respuesta | Bajo |
| Importador | Joya de la corona | solo precision, scoring y observabilidad | Alto si se toca mal |

## Contratos Tecnicos a Exigir

Toda accion IA nueva debe devolver una estructura similar a:

```json
{
  "action_id": "create_purchase_draft",
  "mode": "dry_run",
  "confidence": 0.84,
  "summary": "Se recomienda reponer harina y levadura",
  "reasoning": [
    "Stock proyectado por debajo de 3 dias",
    "El proveedor A mantiene mejor coste unitario"
  ],
  "warnings": [
    "Hay una orden pendiente para uno de los productos"
  ],
  "payload": {},
  "requires_approval": true,
  "audit_meta": {
    "provider": "ollama|ovhcloud|openai",
    "module": "purchases"
  }
}
```

Minimos obligatorios:

- `confidence`
- `summary`
- `warnings`
- `requires_approval`
- `payload`
- `audit_meta`

## Riesgos Principales

1. Duplicar logica de negocio en prompts.
   Mitigacion: la IA propone; el backend recalcula y valida.

2. Exceso de contexto.
   Mitigacion: builders resumidos y payloads maximos por modulo.

3. Acciones irreversibles.
   Mitigacion: borrador + aprobacion + feature flag.

4. PII y datos sensibles.
   Mitigacion: mascara, exclusion y minimizacion por modulo.

5. Degradacion silenciosa del proveedor.
   Mitigacion: health, fallback, metricas y alertado.

6. Tocar `importador`.
   Mitigacion: politica explicita de no reescritura.

## KPI de Exito

- porcentaje de propuestas aceptadas por modulo,
- tiempo ahorrado por flujo,
- reduccion de incidencias operativas detectadas tarde,
- ahorro estimado en compras/produccion,
- precision de prediccion de reorden,
- tasa de conciliaciones sugeridas aceptadas,
- tiempo medio hasta resolucion de alertas IA,
- salud y latencia por proveedor IA.

## Orden Recomendado de Ejecucion

1. Consolidar catalogo, flags y health UI.
2. Completar acciones asistidas de compras e inventario.
3. Abrir CRM y reconciliacion asistida.
4. Construir centro de alertas inteligentes.
5. Lanzar agentes de backoffice en background.
6. Introducir aprendizaje operativo por correccion.

## Definition of Done por Entrega IA

Una entrega IA no se considera lista si no cumple todo esto:

- contexto definido y testeado,
- contrato de respuesta estructurado,
- validacion backend de negocio,
- auditoria y metricas,
- feature flag,
- copy UX clara,
- manejo de errores y fallback,
- sin impacto en `importador`,
- sin duplicar catalogos, prompts o servicios ya existentes.

## Decision Ejecutiva

La estrategia correcta no es "meter IA en todo" de forma autonoma. La estrategia correcta es:

- automatizar lectura, resumen y deteccion,
- asistir con borradores y propuestas en operaciones,
- exigir aprobacion humana en acciones sensibles,
- proteger el importador como activo critico del producto.

Si se sigue este PDT, `RimayPilot` puede convertirse en el centro operativo IA del sistema sin perder control ni romper lo que ya funciona.
