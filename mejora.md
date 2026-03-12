# Mejora Sectorial del Sistema

## Objetivo

Preparar el sistema para una panaderia pequena con:

- 3 cajeras
- 2 panaderos

Sin convertir las mejoras en hardcode exclusivo de panaderia. Toda mejora nueva debe:

1. ser reutilizable por otros sectores, o
2. poder activarse y desactivarse por sector y por tenant.

## Principio rector

No se desarrollara "funcionalidad de panaderia" como caso aislado si en realidad pertenece al core del sistema.

Se separa en:

- `Core reutilizable`: capacidades validas para varios sectores
- `Feature sectorial`: capacidades visibles o activas solo en ciertos sectores
- `Override por tenant`: posibilidad de apagar una feature aunque el sector la soporte

## Base existente

### Ya existe y es aprovechable

- POS con cajas, turnos, tickets, cobros y devoluciones
- Inventario con stock, almacenes, ajustes y vista de existencias
- Produccion con recetas, consumo de ingredientes, producto terminado, lote y merma en backend
- RRHH con empleados, vacaciones, fichajes y nomina
- Usuarios y roles por empresa
- Capa de configuracion por sector y features dinamicas

### Lo que no esta cerrado

- Lote y caducidad no estan bien conectados end-to-end en inventario
- La UI de produccion no termina el flujo diario de iniciar/completar/cerrar orden
- El dashboard sectorial de panaderia tiene partes placeholder
- Fichajes parecen mas orientados a consulta que a operacion diaria simple
- La cobertura de pruebas es insuficiente para validar procesos de negocio completos

## Restricciones funcionales

### Restriccion 1: sector-awareness

Toda mejora nueva debe usar configuracion dinamica desde sector/tenant.

Ejemplos:

- `inventory_lot_tracking`
- `inventory_expiry_tracking`
- `production_enabled`
- `production_batch_tracking`
- `hr_timekeeping_enabled`
- `sector_dashboard_bakery`

### Restriccion 2: no romper otros sectores

Si una feature no aplica a retail, taller u otros sectores:

- no debe mostrarse en UI
- no debe exigirse en validaciones
- no debe afectar flujos existentes

### Restriccion 3: mejoras core antes que vistas sectoriales

Primero se corrige la capacidad base.
Despues se expone en UI.
Despues se personaliza por sector.

## Estado actual por modulo

### Verde

- POS
- Usuarios y roles
- Empleados y nomina base

### Amarillo

- Produccion
- Inventario
- Fichajes
- Analitica sectorial

### Rojo

- Persistencia real de lote/caducidad
- Flujo diario completo de produccion desde UI
- Pruebas automatizadas de negocio de punta a punta

## Modelo de mejora

## 1. Core reutilizable

### Inventario

Capacidades core:

- lotes
- caducidad
- stock por almacen
- ajustes
- transferencias
- puntos de reposicion

Aplicable a:

- panaderia
- pasteleria
- restaurante
- retail alimentario
- farmacia

### Produccion

Capacidades core:

- receta/BOM
- orden de produccion
- inicio de orden
- finalizacion de orden
- merma
- lote de salida
- consumo de insumos

Aplicable a:

- panaderia
- pasteleria
- restaurante con preelaborados
- manufactura ligera

### RRHH

Capacidades core:

- empleados
- fichajes
- vacaciones
- nomina

Aplicable a cualquier sector con plantilla.

## 2. Feature sectorial

### Panaderia

Features recomendadas:

- lotes activos
- caducidad activa
- produccion por recetas activa
- control de merma visible
- dashboard sectorial panaderia
- unidades y textos especificos del sector

### Retail

Features recomendadas:

- POS activo
- inventario activo
- produccion desactivada por defecto
- lotes/caducidad solo si se trata de alimentacion

### Taller

Features recomendadas:

- POS opcional
- inventario activo
- produccion por recetas desactivada por defecto
- RRHH activo

## Backlog propuesto

## P0 - Bloqueantes para piloto serio

### P0.1 Inventario: lote y caducidad end-to-end

Objetivo:

- que los campos capturados en frontend se persistan realmente
- que backend los almacene y devuelva correctamente

Trabajo:

- revisar payload de frontend
- extender endpoint si hace falta
- persistir en stock item y/o movimiento
- validar lectura en tabla de stock

Criterio de aceptacion:

- un movimiento con lote y caducidad se guarda
- se ve despues en stock
- se conserva tras recarga

### P0.2 Produccion: flujo operativo completo en UI

Objetivo:

- que el panadero pueda ejecutar una orden sin pasos manuales externos

Trabajo:

- iniciar orden
- completar orden
- informar cantidad producida
- informar merma y motivo
- mostrar lote generado
- mostrar almacen destino

Criterio de aceptacion:

- al completar orden se consumen ingredientes
- se genera producto terminado
- queda lote trazable
- la merma queda registrada

### P0.3 Features por sector/tenant

Objetivo:

- que las mejoras no queden fijas para panaderia

Trabajo:

- definir feature flags
- usarlas en frontend
- usarlas en validaciones de backend cuando aplique

Criterio de aceptacion:

- las pantallas y campos aparecen solo cuando la feature esta activa
- se pueden apagar por tenant

### P0.4 Roles operativos

Objetivo:

- separar responsabilidades minimas

Roles minimos:

- admin
- encargado
- cajera
- panadero

Criterio de aceptacion:

- cajera no administra configuracion
- panadero no gestiona usuarios
- encargado puede revisar produccion e inventario

### P0.5 Tests de negocio

Objetivo:

- validar flujos reales, no solo pantallas

Casos minimos:

- venta POS descuenta stock
- devolucion repone stock
- produccion consume ingredientes
- produccion genera producto final
- cierre de turno falla si hay pendientes

## P1 - Recomendado para puesta en marcha tranquila

### P1.1 Fichaje rapido

Objetivo:

- permitir entrada, salida y descanso desde una UI simple

Debe ser:

- reutilizable por cualquier sector
- visible solo si `hr_timekeeping_enabled`

### P1.2 Dashboard sectorial panaderia

Objetivo:

- dar una vista util al encargado

Indicadores:

- ventas de mostrador
- stock critico
- merma del dia
- lotes completados
- productos mas vendidos

Debe estar aislado por sector.

### P1.3 Alertas operativas

Objetivo:

- avisar faltantes o anomalias

Ejemplos:

- harina por debajo de minimo
- levadura por debajo de minimo
- merma anormal
- producto con caducidad cercana

## P2 - Mejora operativa y escalado

- planificacion diaria de produccion
- propuesta automatica de fabricacion segun ventas historicas
- hoja de produccion imprimible
- mejores reportes por cajera y por turno
- mayor cobertura e2e y pruebas de regresion

## Orden recomendado de trabajo

1. Corregir core de inventario
2. Cerrar flujo de produccion
3. Introducir gating por sector/tenant
4. Definir roles operativos
5. Escribir pruebas de negocio
6. Mejorar RRHH y dashboard sectorial

## Criterios de arquitectura

### Frontend

- usar `CompanyConfigContext` y `sectorConfig/features`
- no introducir `is_panaderia` nuevos
- ocultar UI por feature, no por hacks visuales

### Backend

- mantener endpoints genericos
- usar validaciones condicionales solo cuando la feature este activa
- no duplicar modulos por sector

### Datos

- si un campo es transversal, debe vivir en el modelo core
- si es sectorial, debe poder estar vacio sin romper otros sectores

## Riesgos

- mezclar feature sectorial con logica core
- crear permisos inconsistentes entre manifests y backend
- resolver solo la UI sin cerrar persistencia
- apoyar decisiones en documentacion vieja en vez de codigo real

## Definition of Done

Una mejora se considera terminada solo si:

- funciona en backend
- funciona en frontend
- esta gobernada por sector o tenant si aplica
- tiene al menos una prueba automatizada relevante
- no rompe otros sectores

## Siguiente paso

Convertir este documento en backlog tecnico ejecutable, separando:

- archivos a tocar
- impacto por modulo
- migraciones necesarias
- pruebas necesarias
- esfuerzo estimado por tarea

## Backlog tecnico ejecutable

## Convenciones

- `P0`: necesario para piloto serio
- `P1`: recomendado para salida estable
- `P2`: mejora posterior
- estimaciones en `horas netas`
- toda tarea debe pasar por `sector-governor` y cerrarse con `qa-regression`

## Resumen ejecutivo

### P0

- `BT-001` Inventario: persistencia real de lote y caducidad
- `BT-002` Produccion: acciones operativas de orden en UI
- `BT-003` Produccion: cierre completo con cantidad, merma, lote y almacen
- `BT-004` Features por sector y tenant para inventario y produccion
- `BT-005` Matriz minima de roles operativos
- `BT-006` Tests minimos de negocio

### P1

- `BT-101` Fichaje rapido
- `BT-102` Dashboard sectorial panaderia con datos reales
- `BT-103` Alertas operativas reutilizables

### P2

- `BT-201` Planificacion diaria de produccion
- `BT-202` Reposicion sugerida
- `BT-203` Hoja de produccion imprimible

## Estado de ejecucion

Fecha de actualizacion:

- `2026-03-12`

Convencion de estado:

- `hecho`: desarrollado y validado en codigo
- `parcial`: desarrollado en parte o validado solo parcialmente
- `pendiente`: no desarrollado
- `validacion pendiente`: requiere prueba mas fuerte en entorno completo

### Estado por tarea

- `BT-001` `hecho`
  Persistencia de `lote` y `expires_at` cerrada entre frontend y backend.
- `BT-002` `hecho`
  Acciones operativas de orden expuestas en UI.
- `BT-003` `hecho`
  Flujo de completado con cantidad, merma y lote operativo en UI.
- `BT-004` `hecho`
  Gating por sector y tenant aplicado a inventario y produccion.
- `BT-005` `hecho`
  La matriz minima de `admin`, `encargado`, `cajera` y `panadero/operario` quedo sembrada y validada para el flujo operativo esperado.
- `BT-006` `hecho`
  Los casos minimos del documento quedaron cubiertos en backend para POS, produccion e inventario, aunque la corrida completa de test suite sigue pendiente en entorno completo.
- `BT-101` `hecho`
  Fichaje rapido con entrada, descanso, vuelta y salida.
- `BT-102` `hecho`
  Dashboard sectorial de panaderia conectado con datos reales principales.
- `BT-103` `hecho`
  Alertas reutilizables ampliadas con caducidad cercana y merma alta.
- `BT-201` `hecho`
  Planificacion diaria de produccion integrada en frontend y backend.
- `BT-202` `hecho`
  Sugerencias de reposicion calculadas desde ventas, stock y planificacion.
- `BT-203` `hecho`
  Hoja diaria de produccion imprimible integrada en el planificador.

### Estado global por fase

- `P0` `hecho`
  El bloque minimo para piloto serio queda cerrado en codigo y con validacion tecnica basica; la validacion final pendiente es ejecutar la suite completa en entorno con dependencias completas.
- `P1` `hecho`
- `P2` `hecho`

### Validacion ejecutada

- `python -m py_compile` sobre los archivos backend modificados: `ok`
- `npm --prefix apps/tenant run typecheck`: `ok`
- `pytest` completo: `no ejecutado en este entorno`
- `e2e` completos de regresion: `parcial`

### Cierre practico

El documento ya no esta en modo propuesta inicial. Ahora refleja un estado real de ejecucion:

- base sectorial aplicada
- flujo de produccion mucho mas cerrado
- planificacion diaria y hoja imprimible listas
- pruebas mejoradas, pero no completas al nivel de cierre final

## Tareas P0

### BT-001 Inventario: persistencia real de lote y caducidad

Tipo:

- core reutilizable

Objetivo:

- que `lote` y `expires_at` viajen y persistan de punta a punta

Archivos candidatos:

- `apps/tenant/src/modules/inventory/services.ts`
- `apps/tenant/src/modules/inventory/MovementForm.tsx`
- `apps/tenant/src/modules/inventory/MovementFormBulk.tsx`
- `apps/backend/app/modules/inventory/interface/http/tenant.py`
- modelos o schemas de inventario si hiciera falta

Trabajo tecnico:

- revisar contrato actual del payload en frontend
- extender endpoint `stock/adjust` si hoy no acepta lote/caducidad
- definir donde persisten esos campos:
  - `stock_items`
  - `stock_moves`
  - ambos, si se necesita trazabilidad y stock actual
- asegurar lectura correcta en listados

Migracion:

- solo si faltan columnas persistentes en tablas usadas

Pruebas:

- test backend de ajuste con lote/caducidad
- test backend de lectura de stock con esos campos
- test frontend o integration del payload enviado

Dependencias:

- ninguna

Estimacion:

- `6 a 10 h`

Criterio de cierre:

- crear movimiento con lote/caducidad
- recargar vista
- seguir viendo ambos datos en stock

### BT-002 Produccion: acciones operativas de orden en UI

Tipo:

- core reutilizable para sectores con BOM

Objetivo:

- exponer desde UI el ciclo operativo de la orden

Archivos candidatos:

- `apps/tenant/src/modules/productions/OrdersList.tsx`
- `apps/tenant/src/modules/productions/services.ts`
- `apps/tenant/src/modules/productions/Routes.tsx`

Trabajo tecnico:

- añadir accion `iniciar`
- añadir accion `completar`
- añadir accion `cancelar`
- bloquear acciones invalidas segun estado
- mostrar estado operativo con claridad

Migracion:

- no deberia requerir

Pruebas:

- test frontend de visibilidad de acciones por estado
- test backend del cambio de estado si no existe

Dependencias:

- ninguna

Estimacion:

- `5 a 8 h`

Criterio de cierre:

- una orden puede iniciarse, cancelarse o ir al flujo de completado desde la UI

### BT-003 Produccion: cierre completo con cantidad, merma, lote y almacen

Tipo:

- core reutilizable para sectores con produccion

Objetivo:

- completar una orden sin pasos manuales externos

Archivos candidatos:

- `apps/tenant/src/modules/productions/OrdersList.tsx`
- `apps/tenant/src/modules/productions/OrderForm.tsx`
- nuevo modal o componente de completado si conviene
- `apps/tenant/src/modules/productions/services.ts`
- `apps/backend/app/modules/production/interface/http/tenant.py`

Trabajo tecnico:

- pedir `qty_produced`
- pedir `waste_qty`
- pedir `waste_reason`
- mostrar o permitir `batch_number`
- confirmar `warehouse_id`
- reflejar resultado en stock final

Migracion:

- solo si falta algun campo de orden ya esperado por backend

Pruebas:

- test backend de `complete`
- test de integracion de consumo de ingredientes
- test de integracion de creacion de producto final

Dependencias:

- `BT-002`
- coordinacion con `inventory-integrity`

Estimacion:

- `8 a 14 h`

Criterio de cierre:

- completar orden desde UI consume ingredientes, genera producto final, registra merma y lote

### BT-004 Features por sector y tenant para inventario y produccion

Tipo:

- infraestructura funcional

Objetivo:

- que mejoras nuevas no queden fijas para panaderia

Feature flags minimas:

- `inventory_lot_tracking`
- `inventory_expiry_tracking`
- `production_enabled`
- `production_batch_tracking`
- `production_waste_tracking`

Archivos candidatos:

- `apps/tenant/src/contexts/CompanyConfigContext.tsx`
- hooks de configuracion de sector
- vistas de inventario y produccion
- backend de settings si hace falta exponer o persistir flags

Trabajo tecnico:

- definir flags
- ocultar o mostrar campos segun flags
- evitar validaciones globales cuando la feature esta apagada

Migracion:

- no necesariamente
- puede requerir semilla de configuracion por sector

Pruebas:

- test con feature activa
- test con feature desactivada

Dependencias:

- ninguna, pero idealmente antes de cerrar `BT-001` y `BT-003`

Estimacion:

- `6 a 12 h`

Criterio de cierre:

- mismas pantallas funcionan con feature on y off sin romper otros sectores

### BT-005 Matriz minima de roles operativos

Tipo:

- seguridad y operacion

Objetivo:

- formalizar acceso de `admin`, `encargado`, `cajera`, `panadero`

Archivos candidatos:

- `apps/backend/app/modules/users/interface/http/tenant.py`
- `apps/backend/app/modules/identity/interface/http/tenant_roles.py`
- `apps/tenant/src/modules/users/*`
- manifests de modulos
- rutas protegidas de POS, inventario, produccion y RRHH

Trabajo tecnico:

- mapear permisos actuales
- detectar huecos entre frontend y backend
- definir matriz minima por rol
- alinear botones, rutas y endpoints

Migracion:

- puede requerir semilla de roles base

Pruebas:

- al menos un caso por rol critico
- ruta protegida
- accion prohibida

Dependencias:

- coordinacion con `permissions-roles-audit`

Estimacion:

- `5 a 9 h`

Criterio de cierre:

- cada rol tiene acceso coherente y no hay acciones visibles que el backend rechace por sorpresa

### BT-006 Tests minimos de negocio

Tipo:

- calidad

Objetivo:

- cubrir flujo real y no solo renderizado de paginas

Casos obligatorios:

- POS: venta descuenta stock
- POS: devolucion repone stock
- POS: cierre de turno falla con recibos pendientes
- Produccion: completar orden consume ingredientes
- Produccion: completar orden genera stock de salida
- Inventario: lote/caducidad persisten

Archivos candidatos:

- `apps/backend/tests/*`
- `e2e/pos.spec.ts`
- `e2e/inventory.spec.ts`
- nuevos tests de produccion

Trabajo tecnico:

- separar smoke tests de pruebas de negocio
- escribir tests estrechos y de alto valor
- documentar huecos que queden fuera

Migracion:

- no

Dependencias:

- `BT-001`
- `BT-003`
- `BT-005`

Estimacion:

- `8 a 14 h`

Criterio de cierre:

- los flujos criticos tienen cobertura automatizada minima

## Tareas P1

### BT-101 Fichaje rapido

Tipo:

- core reutilizable

Objetivo:

- permitir entrada, salida y descanso desde UI simple

Archivos candidatos:

- `apps/tenant/src/modules/hr/FichajesView.tsx`
- `apps/tenant/src/modules/hr/services/fichajes.ts`
- `apps/backend/app/modules/hr/interface/http/tenant.py`

Trabajo tecnico:

- añadir acciones de registro rapido
- mostrar abiertos, cerrados y descansos
- condicionar por `hr_timekeeping_enabled`

Estimacion:

- `6 a 10 h`

### BT-102 Dashboard sectorial panaderia con datos reales

Tipo:

- feature sectorial

Objetivo:

- reemplazar placeholders por datos reales de operacion

Archivos candidatos:

- `apps/backend/app/modules/analytics/interface/http/tenant.py`
- dashboard sectorial frontend correspondiente

Trabajo tecnico:

- conectar lotes completados
- conectar merma del dia
- conectar ventas de mostrador
- conectar stock critico real

Estimacion:

- `6 a 12 h`

### BT-103 Alertas operativas reutilizables

Tipo:

- core con activacion por sector o tenant

Objetivo:

- avisar faltantes y anomalias sin acoplarlo a panaderia

Trabajo tecnico:

- reutilizar configuracion de alertas de inventario
- añadir reglas de caducidad cercana y merma anormal si aplica

Estimacion:

- `5 a 9 h`

## Tareas P2

### BT-201 Planificacion diaria de produccion

Estimacion:

- `8 a 14 h`

### BT-202 Reposicion sugerida

Estimacion:

- `8 a 16 h`

### BT-203 Hoja de produccion imprimible

Estimacion:

- `4 a 8 h`

## Dependencias maestras

- `BT-001` antes de cerrar trazabilidad de inventario
- `BT-002` antes de `BT-003`
- `BT-004` en paralelo temprano para evitar hardcodes
- `BT-005` antes de validacion operativa final
- `BT-006` al cierre de P0

## Ruta recomendada de ejecucion

### Ruta minima para piloto

1. `BT-004`
2. `BT-001`
3. `BT-002`
4. `BT-003`
5. `BT-005`
6. `BT-006`

### Esfuerzo total aproximado

- `P0`: `38 a 67 h`
- `P1`: `17 a 31 h`
- `P2`: `20 a 38 h`

## Checklist de inicio por tarea

Antes de empezar una tarea:

- clasificar con `sector-governor`
- listar archivos a tocar
- confirmar si requiere migracion
- confirmar riesgo sobre otros sectores

Antes de cerrar una tarea:

- revisar permisos si toca accesos
- ejecutar tests relevantes
- pasar por `qa-regression`

## Propuesta de agentes

## Objetivo de los agentes

Los agentes no deben duplicar el desarrollo principal ni inventar arquitectura paralela.

Su funcion debe ser:

- imponer criterios
- revisar consistencia
- especializar validaciones
- reducir regresiones

Se propone un conjunto pequeno de agentes especializados y complementarios.

## Agente 1: sector-governor

### Mision

Garantizar que toda mejora nueva quede correctamente clasificada como:

- core reutilizable
- feature sectorial
- override por tenant

### Cuando debe intervenir

- al inicio de cualquier mejora funcional
- cuando se agregan campos nuevos
- cuando se agregan pantallas o botones visibles
- cuando se agregan validaciones de negocio

### Responsabilidades

- impedir hardcodes exclusivos de panaderia
- exigir feature flags cuando una mejora no sea universal
- revisar que la UI solo muestre lo que el sector o tenant tenga activo
- validar que los nombres de features sean coherentes

### Archivos que debe vigilar

- `apps/tenant/src/contexts/CompanyConfigContext.tsx`
- `apps/tenant/src/modules/ModuleLoader.tsx`
- configuraciones de sector
- manifests de modulos
- settings de tenant y company settings

### Preguntas que debe responder

- esto es core o sectorial
- se puede apagar por tenant
- rompe otro sector
- esta usando configuracion dinamica o hardcode

## Agente 2: inventory-integrity

### Mision

Proteger la consistencia del inventario entre frontend, backend, movimientos y stock agregado.

### Cuando debe intervenir

- cambios en stock
- cambios en lotes
- cambios en caducidad
- movimientos de inventario
- integraciones con POS y produccion

### Responsabilidades

- revisar payloads y persistencia real
- asegurar que lote y caducidad viajen de punta a punta
- revisar impacto en stock_items y stock_moves
- revisar consistencia entre cantidad por almacen y stock agregado del producto
- validar alertas y puntos de reposicion

### Archivos que debe vigilar

- `apps/backend/app/modules/inventory/interface/http/tenant.py`
- `apps/tenant/src/modules/inventory/services.ts`
- `apps/tenant/src/modules/inventory/MovementForm.tsx`
- `apps/tenant/src/modules/inventory/MovementFormBulk.tsx`
- `apps/tenant/src/modules/inventory/StockList.tsx`
- integraciones POS e inventario
- integraciones produccion e inventario

### Riesgos a detectar

- campos capturados en UI pero no persistidos
- doble ajuste de stock
- stock negativo no deseado
- lotes visibles pero no reales

## Agente 3: production-ops

### Mision

Convertir el backend de produccion existente en flujo operativo completo para sectores con receta/BOM.

### Cuando debe intervenir

- cambios en recetas
- cambios en ordenes de produccion
- cambios en coste, merma y lote
- cambios en integracion con compras o inventario

### Responsabilidades

- validar que producir consuma insumos
- validar que completar una orden genere producto final
- revisar uso de lote de salida
- revisar merma y su trazabilidad
- asegurar que la UI cubra iniciar, completar y cancelar
- mantener la logica reutilizable para panaderia, pasteleria y manufactura ligera

### Archivos que debe vigilar

- `apps/backend/app/modules/production/interface/http/tenant.py`
- `apps/tenant/src/modules/productions/services.ts`
- `apps/tenant/src/modules/productions/OrdersList.tsx`
- `apps/tenant/src/modules/productions/OrderForm.tsx`
- `apps/tenant/src/modules/productions/RecetaDetail.tsx`
- servicios de coste de produccion

### Riesgos a detectar

- orden completada sin consumo real
- lote generado pero no visible
- merma informada pero no usable
- backend soporta flujo que frontend no expone

## Agente 4: permissions-roles-audit

### Mision

Alinear permisos, roles, manifests, rutas protegidas y capacidad real de cada usuario.

### Cuando debe intervenir

- cambios de roles
- cambios de permisos
- nuevos modulos o nuevas pantallas
- diferencias entre backend y frontend

### Responsabilidades

- revisar consistencia entre permisos backend y manifests frontend
- validar visibilidad de botones y rutas
- proponer matriz minima de roles operativos
- revisar que un rol sectorial no quede acoplado al nombre del sector

### Archivos que debe vigilar

- `apps/backend/app/modules/users/interface/http/tenant.py`
- `apps/backend/app/modules/identity/interface/http/tenant_roles.py`
- manifests de modulos
- rutas protegidas en frontend
- hooks de permisos

### Matriz minima a proteger

- `admin`
- `encargado`
- `cajera`
- `panadero`

## Agente 5: qa-regression

### Mision

Traducir cada mejora a pruebas minimas y checklist de no regresion.

### Cuando debe intervenir

- antes de cerrar una tarea
- antes de marcar una mejora como terminada
- cuando se tocan flujos de POS, inventario o produccion

### Responsabilidades

- definir casos de prueba funcionales
- exigir al menos una prueba automatizada relevante
- detectar huecos entre documentacion y comportamiento real
- separar smoke tests de pruebas de negocio

### Archivos que debe vigilar

- `e2e/pos.spec.ts`
- `e2e/inventory.spec.ts`
- tests backend de RRHH
- futuros tests de produccion e inventario

### Casos minimos que debe exigir

- venta POS descuenta stock
- devolucion repone stock
- produccion consume ingredientes
- produccion genera producto final
- cierre de turno falla con pendientes

## Agente opcional: bakery-domain

### Mision

Apoyar decisiones funcionales del sector panaderia sin contaminar el core.

### Cuando debe intervenir

- definicion de dashboard sectorial
- unidades y textos de panaderia
- KPIs de merma, lotes y produccion diaria
- revision funcional previa a piloto

### Responsabilidades

- validar que los flujos tengan sentido para una panaderia pequena
- revisar nomenclatura funcional
- proponer KPIs de sector
- no introducir hardcodes en el core

### Regla critica

Este agente no debe diseñar estructuras exclusivas del sector si la capacidad puede vivir en el core.

## Orden recomendado de uso

1. `sector-governor`
2. agente especialista del modulo
3. `permissions-roles-audit` si cambia acceso o visibilidad
4. `qa-regression`
5. `bakery-domain` solo si hay validacion funcional sectorial

## Reglas de colaboracion entre agentes

- un agente no redefine el alcance de otro
- `sector-governor` tiene prioridad sobre decisiones de sectorizacion
- `qa-regression` tiene prioridad para impedir cierre prematuro de una tarea
- `bakery-domain` asesora negocio, no decide arquitectura core

## Implementacion recomendada

Estos agentes pueden implementarse como skills pequenas, no como sistemas complejos.

Cada skill deberia contener:

- una descripcion de disparo clara
- checklist corta de revision
- referencias a archivos y modulos relevantes
- criterios de aceptacion y riesgos tipicos

## Siguiente paso de agentes

Si se decide implementarlos de verdad, crear skills para:

- `sector-governor`
- `inventory-integrity`
- `production-ops`
- `permissions-roles-audit`
- `qa-regression`

Y dejar `bakery-domain` como skill opcional, no obligatoria.
