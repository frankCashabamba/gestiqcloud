# GestiQCloud — Documento de Desarrollo
_Versión 1.0_

## 1. Objetivo del documento

Este documento define una guía práctica de desarrollo para **GestiQCloud**, con foco en:

- prioridades técnicas
- reducción de riesgo
- orden de ejecución
- calidad de producto
- preparación para salida a mercado

No está orientado a inversión ni marketing.  
Está pensado para servir como **documento interno de ejecución** para desarrollo.

---

## 2. Contexto del producto

**GestiQCloud** es un SaaS ERP/CRM multi-tenant orientado a PYMEs hispanohablantes, con especial foco en **España y Ecuador**, y con diferenciadores claros:

- facturación electrónica nativa
- POS + inventario + ventas + compras + contabilidad
- arquitectura cloud multi-tenant
- PWA/offline-first
- AI Copilot + OCR/AI para documentos
- plantillas por sector
- pasarelas de pago locales

El principal reto actual no parece ser “falta de módulos”, sino:

1. consolidar seguridad y arquitectura
2. endurecer operaciones
3. simplificar experiencia
4. preparar monetización
5. soportar adopción real

---

## 3. Principios de desarrollo

### 3.1 Prioridad por impacto real
Cada desarrollo nuevo debe responder a una de estas preguntas:

- ¿reduce riesgo crítico?
- ¿aumenta conversión a cliente?
- ¿mejora retención?
- ¿facilita operación interna?
- ¿refuerza el diferenciador principal?

Si una funcionalidad no cumple al menos una, no debe ser prioritaria.

### 3.2 Seguridad antes que amplitud
En un sistema multi-tenant, la prioridad absoluta es evitar fugas entre tenants, errores fiscales y corrupción de datos.

### 3.3 Profundidad antes que más módulos
Es preferible tener:

- ventas excelente
- POS excelente
- facturación electrónica excelente
- inventario excelente

que 30 módulos mediocres.

### 3.4 Producto operable
Toda feature nueva debe venir acompañada de:

- logging
- manejo de errores
- observabilidad
- control de permisos
- tests mínimos
- rollback o feature flag si aplica

---

## 4. Objetivos técnicos prioritarios

## 4.1 Objetivo P0 — Seguridad multi-tenant
### Meta
Garantizar aislamiento real entre tenants a nivel de base de datos y aplicación.

### Tareas
- activar RLS completo en PostgreSQL para tablas de negocio
- revisar políticas por tabla
- validar que todas las queries incluyan contexto de tenant
- eliminar accesos inseguros por omisión
- añadir tests automáticos de aislamiento entre tenants
- revisar exports, reportes, búsquedas, dashboards y Copilot

### Criterio de terminado
- un tenant no puede leer, editar ni inferir datos de otro tenant
- tests de aislamiento pasan en CI
- endpoints críticos auditados

---

## 4.2 Objetivo P0 — Billing y monetización
### Meta
Permitir cobro real del producto.

### Tareas
- definir planes oficiales
- implementar suscripciones
- integrar Stripe Billing
- gestionar estados: trial, active, past_due, canceled
- límites por plan:
  - usuarios
  - facturas
  - módulos
  - OCR/AI usage
- añadir pantalla de suscripción y facturación
- webhooks de Stripe para sincronización de estado
- políticas de grace period y downgrade

### Criterio de terminado
- un tenant puede registrarse, iniciar trial, pagar y continuar operando sin intervención manual

---

## 4.3 Objetivo P0 — Landing + onboarding conectado al producto
### Meta
Cerrar el circuito comercial completo.

### Tareas
- landing page con propuesta de valor clara
- signup auto-servicio
- creación de tenant automatizada
- wizard inicial por sector
- selección de país
- configuración mínima fiscal
- alta de primer usuario admin
- datos demo opcionales

### Criterio de terminado
- una pyme puede descubrir el producto, registrarse y comenzar a usarlo en menos de 20 minutos

---

## 4.4 Objetivo P1 — Endurecimiento de migraciones
### Meta
Eliminar fragilidad operacional.

### Tareas
- migrar desde SQL manual frágil a un sistema trazable
- evaluar Alembic o sistema propio robusto
- registrar versión actual por entorno
- hacer rollback seguro cuando aplique
- prohibir scripts con silenciamiento de errores tipo `|| true`
- documentar proceso de despliegue DB

### Criterio de terminado
- cada cambio de esquema tiene trazabilidad, orden, rollback y validación

---

## 4.5 Objetivo P1 — Feature flags
### Meta
Desplegar sin romper tenants.

### Tareas
- sistema de feature flags por:
  - entorno
  - tenant
  - país
  - plan
  - usuario interno/beta
- soporte para rollout parcial
- panel básico de gestión
- integración con frontend y backend

### Criterio de terminado
- cualquier feature sensible puede activarse progresivamente sin redeploy completo

---

## 4.6 Objetivo P1 — Observabilidad operativa
### Meta
Tener visibilidad real de producción.

### Tareas
- estandarizar logs estructurados
- correlación por request_id, tenant_id, user_id
- dashboards de errores por módulo
- métricas de:
  - tiempos de respuesta
  - colas Celery
  - reintentos SRI/SII
  - fallos OCR/AI
  - errores de facturación
- alertas críticas
- monitoreo de jobs colgados

### Criterio de terminado
- cualquier incidente importante puede detectarse y trazarse en minutos

---

## 5. Áreas funcionales prioritarias

## 5.1 Núcleo comercial
Estas áreas deben tratarse como core del producto inicial:

- ventas
- POS
- inventario
- facturación
- facturación electrónica
- clientes
- caja/bancos

### Objetivo
Llevar este núcleo a un nivel sobresaliente antes de seguir ampliando módulos.

### Recomendación
Definir una matriz de profundidad por módulo:

- indispensable
- deseable
- futuro

---

## 5.2 Contabilidad y cumplimiento
Dado que el producto compite por cumplimiento local, esta capa es crítica.

### Prioridades
- robustecer plan de cuentas y asientos
- validar conciliación bancaria
- endurecer trazabilidad fiscal
- estados claros de documentos electrónicos
- reintentos seguros para SRI/SII
- auditoría de cambios

### Regla
Nunca sacrificar consistencia contable por velocidad de entrega.

---

## 5.3 AI Copilot
La IA debe evolucionar de “feature llamativa” a “acelerador real de operación”.

### Fases sugeridas
#### Fase 1
- consultas read-only confiables
- insights explicables
- sugerencias contextuales

#### Fase 2
- drafts accionables
- asistentes por flujo:
  - factura
  - pedido
  - compra
  - transferencia
  - cobranza

#### Fase 3
- agente conversacional controlado
- ejecución con confirmación explícita
- trazabilidad de cada acción generada por IA

### Reglas
- toda acción de escritura por IA debe ser auditable
- la IA no debe saltarse reglas fiscales o permisos
- toda salida de IA debe poder desactivarse por tenant

---

## 5.4 OCR / importador inteligente
Este módulo puede ser un gran diferenciador operativo.

### Prioridades
- mejorar precisión por tipo documental
- scoring de confianza visible
- validación humana rápida
- aprendizaje de correcciones frecuentes
- métricas por proveedor y por layout

### KPI deseado
- reducir tiempo de carga manual de documentos en al menos 70%

---

## 6. Arquitectura recomendada

## 6.1 Mantener modular monolith por ahora
No conviene fragmentar a microservicios salvo necesidad real.

### Motivos
- menor complejidad operativa
- velocidad de desarrollo
- menos coste cognitivo
- mejor consistencia transaccional

### Separar sólo cuando:
- haya cuellos de botella claros
- una carga sea muy distinta del resto
- el equipo pueda operarlo bien

## 6.2 Componentes que sí pueden vivir desacoplados
- workers Celery
- OCR/AI pipeline
- webhooks
- facturación electrónica
- tareas pesadas de generación documental

## 6.3 Contratos internos
Formalizar contratos entre módulos:

- DTOs claros
- eventos internos
- validaciones compartidas
- tipado consistente frontend/backend

---

## 7. Calidad de código y deuda técnica

## 7.1 Backend
### Estándares mínimos
- tipado consistente
- servicios y repositorios claros
- evitar lógica de negocio en routers
- validación de input con esquemas explícitos
- manejo homogéneo de errores

### Deuda a vigilar
- SQL crudo creciendo sin patrón
- duplicación de lógica fiscal
- utilidades genéricas mal definidas
- permisos dispersos

## 7.2 Frontend
### Estándares mínimos
- reducir warnings a cero
- componentes reutilizables
- estado bien delimitado
- rutas lazy y seguras
- control de permisos por módulo
- manejo de errores y estados vacíos

### Riesgos actuales
- sidebar sobrecargado
- demasiados módulos visibles desde el inicio
- complejidad creciente del admin
- acoplamiento entre pantallas y APIs

---

## 8. UX de desarrollo prioritario

## 8.1 Modo express
Diseñar una experiencia inicial con sólo:

- ventas
- POS
- inventario
- facturación

Ocultar el resto hasta que el negocio esté operativo.

## 8.2 Progressive disclosure
Mostrar complejidad gradualmente según:

- sector
- país
- plan
- madurez del tenant

## 8.3 Estados claros
Cada flujo crítico debe mostrar claramente:

- pendiente
- procesando
- aceptado
- rechazado
- reintento
- error recuperable
- error definitivo

Especialmente en:
- SRI/SII
- pagos
- OCR
- sincronizaciones
- exports

---

## 9. Seguridad

## 9.1 Seguridad crítica
- RLS activo
- permisos por rol
- validación por tenant
- secretos fuera del código
- rotación de credenciales
- cookies seguras
- CSRF donde aplique
- rate limiting
- auditoría de acciones sensibles

## 9.2 Áreas de auditoría obligatoria
- exports masivos
- búsquedas globales
- reportes agregados
- importaciones
- webhooks
- AI prompts con datos sensibles
- generación de PDFs y documentos fiscales

## 9.3 Auditoría funcional
Registrar acciones sensibles:
- emisión y anulación de factura
- cambios de inventario
- asientos contables
- devoluciones
- cambios de configuración fiscal
- acciones generadas por IA

---

## 10. Testing

## 10.1 Pirámide recomendada
### Unit tests
Para reglas de negocio puras:
- impuestos
- descuentos
- estados de documentos
- validaciones contables
- pricing y límites

### Integration tests
Para:
- DB
- RLS
- Celery
- proveedores externos simulados
- webhooks
- storage

### E2E
Flujos críticos:
- signup
- onboarding
- venta POS
- emisión factura electrónica
- compra
- conciliación
- importación OCR
- upgrade de plan

## 10.2 Casos críticos obligatorios
- aislamiento entre tenants
- doble envío por reintentos
- idempotencia en pagos
- errores del proveedor SRI/SII
- caída parcial de Redis o workers
- expiración de sesión
- límites por plan
- failover de AI provider

---

## 11. DevOps y operación

## 11.1 Objetivos
- despliegue repetible
- rollback claro
- monitoreo simple
- menor dependencia manual

## 11.2 Recomendaciones
- estandarizar entornos
- consolidar scripts de deploy
- healthchecks por servicio
- backups verificados
- restore probado
- separación clara entre staging y producción
- smoke tests post deploy

## 11.3 Riesgos operativos actuales
- mezcla de infra en varios sitios
- dependencia alta de configuración manual
- demasiadas piezas para un equipo pequeño

### Recomendación práctica
Reducir complejidad operativa donde no haya ventaja competitiva.

---

## 12. Roadmap técnico recomendado

## Próximos 30 días
### Objetivo
Estar listos para uso real con seguridad y cobro.

### Entregables
- RLS completo
- billing básico
- landing + signup + trial
- revisión de permisos
- tests de aislamiento
- reducción de warnings críticos frontend
- checklist de producción

## Próximos 90 días
### Objetivo
Conseguir primeros clientes y operar sin incendios.

### Entregables
- feature flags
- observabilidad mejorada
- onboarding mejorado
- dashboards de errores y colas
- hardening SRI/SII
- límites por plan
- mejoras UX modo express
- soporte básico interno

## Próximos 6-12 meses
### Objetivo
Profundizar núcleo y mejorar retención.

### Entregables
- AI Copilot más útil y conversacional
- dashboard contadores
- plantillas sectoriales maduras
- migraciones robustas
- auto-scaling o capacity planning serio
- integraciones clave como WhatsApp
- data model y reporting más sólidos

---

## 13. Qué no hacer ahora

No priorizar de inmediato:

- más países antes de validar uno
- más módulos grandes sin usuarios activos
- microservicios por moda
- app móvil nativa si la PWA aún no está pulida
- features vistosas sin impacto en activación o retención
- personalizaciones extremas por cliente demasiado pronto

---

## 14. Definición de éxito del área de desarrollo

Desarrollo va bien si logra esto:

- producción estable
- cero fugas entre tenants
- onboarding corto
- cobro funcionando
- núcleo comercial sólido
- facturación electrónica confiable
- incidentes detectables y trazables
- releases controlados
- feedback real entrando al roadmap

No va bien si:

- se siguen añadiendo módulos sin uso real
- la seguridad multi-tenant sigue incompleta
- no existe monetización
- el sistema depende de heroicidad manual para operar

---

## 15. Conclusión

GestiQCloud ya parece tener una base técnica fuerte. El siguiente paso de desarrollo no es “construir más”, sino **cerrar riesgos, simplificar, monetizar y endurecer lo existente**.

La prioridad correcta no es el módulo número 26.  
La prioridad correcta es esta:

1. seguridad multi-tenant
2. monetización
3. onboarding comercial
4. profundidad en núcleo operativo
5. observabilidad
6. despliegue controlado
7. soporte a primeros clientes reales

Si se ejecuta este orden, el producto queda preparado para pasar de “software prometedor” a “SaaS operable y vendible”.
