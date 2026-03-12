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
