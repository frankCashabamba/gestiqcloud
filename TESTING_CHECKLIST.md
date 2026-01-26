# 🧪 Testing Checklist - Frontend Completado

**Fecha:** Enero 19, 2026
**Componentes a Probar:** Dashboard, Notificaciones, Webhooks

---

## ✅ Dashboard (`/admin/dashboard`)

### Carga Inicial
- [ ] Página carga sin errores
- [ ] Spinner aparece durante carga
- [ ] Datos se cargan correctamente
- [ ] No hay warnings en consola

### KPIs (Stats)
- [ ] Se muestran 5 cards de KPIs
- [ ] Valores numéricos son correctos
- [ ] Iconos son visibles
- [ ] Colores de fondo son correctos

### KPI Board
- [ ] Tabla de "Métodos por Empresa" se muestra
- [ ] Tabla de "Tendencias Mensuales" se muestra
- [ ] Indicadores de rendimiento se muestran
- [ ] Las barras de progreso funcionan correctamente

### Auto-refresh
- [ ] Dashboard se actualiza cada 30 segundos
- [ ] Contador de refresh funciona
- [ ] Botón "Actualizar" funciona manualmente

### Últimas Empresas
- [ ] Se muestra grid con últimas empresas
- [ ] Formato de fechas es correcto
- [ ] Cards tienen hover effect

### Error Handling
- [ ] Simular error en API y verificar mensaje
- [ ] Botón de "Reintentar" funciona
- [ ] No hay crash de página

### Responsive
- [ ] Desktop (1920px): todo visible
- [ ] Tablet (768px): layout se adapta
- [ ] Mobile (375px): componentes stackeados verticalmente

---

## ✅ Notificaciones (`/admin/notifications`)

### Carga Inicial
- [ ] Página carga sin errores
- [ ] Lista de notificaciones aparece
- [ ] Contador de "Sin leer" es correcto

### Filtros
- [ ] Botón "Todas" muestra todas las notificaciones
- [ ] Botón "Sin leer" filtra correctamente
- [ ] Contador se actualiza al cambiar filtro

### Notificaciones
- [ ] Cada notificación muestra:
  - [ ] Ícono del tipo
  - [ ] Título
  - [ ] Mensaje
  - [ ] Entidad relacionada (si aplica)
  - [ ] Timestamp

### Acciones
- [ ] Click en notificación sin leer la marca como leída
- [ ] Botón "Marcar todas como leídas" funciona
- [ ] Contador disminuye al marcar como leído

### Auto-refresh
- [ ] Se actualiza cada 10 segundos
- [ ] Nuevas notificaciones aparecen automáticamente
- [ ] No interrumpe interacción del usuario

### Error Handling
- [ ] Simular error en API
- [ ] Mensaje de error aparece
- [ ] Usuario puede reintentar

### Responsive
- [ ] Desktop: lista completa visible
- [ ] Tablet: layout adaptado
- [ ] Mobile: lista scrollable

---

## ✅ Webhooks (`/admin/webhooks`)

### Carga Inicial
- [ ] Página carga sin errores
- [ ] Tabla de webhooks aparece
- [ ] Botón "Nuevo Webhook" está visible

### Tabla de Webhooks
- [ ] Se muestran columnas:
  - [ ] URL
  - [ ] Eventos
  - [ ] Estado (Activo/Inactivo)
  - [ ] Acciones

### Indicadores
- [ ] Badge de estado es verde para activos
- [ ] Badge de estado es gris para inactivos
- [ ] Eventos se muestran con límite (+N si hay más)

### Acciones
- [ ] Botón "Probar" funciona
  - [ ] Muestra resultado de test
  - [ ] Status code es visible
  - [ ] Success/Error es claro
- [ ] Botón "Editar" está funcional (placeholder OK por ahora)
- [ ] Botón "Eliminar" funciona
  - [ ] Pide confirmación
  - [ ] Remueve webhook de lista
  - [ ] Mensaje de éxito aparece

### Logs
- [ ] Clickear webhook muestra logs
- [ ] Cada log muestra:
  - [ ] Status (✓/✗)
  - [ ] Evento
  - [ ] Código de respuesta
  - [ ] Timestamp
- [ ] Click en log lo expande
- [ ] Payload y respuesta se muestran en expanded view
- [ ] Código es legible (monospace)

### Error Handling
- [ ] Simular error al cargar webhooks
- [ ] Mensaje de error aparece
- [ ] Botón "Reintentar" funciona

### Responsive
- [ ] Desktop: tabla completa
- [ ] Tablet: tabla adaptada
- [ ] Mobile: tabla vertical o scrollable

---

## 🌐 Testing por Navegador

### Chrome/Edge (Chromium)
- [ ] Dashboard: ✅ OK
- [ ] Notificaciones: ✅ OK
- [ ] Webhooks: ✅ OK

### Firefox
- [ ] Dashboard: ✅ OK
- [ ] Notificaciones: ✅ OK
- [ ] Webhooks: ✅ OK

### Safari
- [ ] Dashboard: ✅ OK
- [ ] Notificaciones: ✅ OK
- [ ] Webhooks: ✅ OK

---

## 📱 Responsive Design Breakpoints

### Mobile (≤600px)
- [ ] Dashboard: ✅ OK
- [ ] Notificaciones: ✅ OK
- [ ] Webhooks: ✅ OK

### Tablet (601px - 1024px)
- [ ] Dashboard: ✅ OK
- [ ] Notificaciones: ✅ OK
- [ ] Webhooks: ✅ OK

### Desktop (≥1025px)
- [ ] Dashboard: ✅ OK
- [ ] Notificaciones: ✅ OK
- [ ] Webhooks: ✅ OK

---

## 🔗 Integración

### Routing
- [ ] `/admin/dashboard` carga correctamente
- [ ] `/admin/notifications` carga correctamente
- [ ] `/admin/webhooks` carga correctamente
- [ ] Links en sidebar funcionan (si existen)

### Autenticación
- [ ] Requiere login para acceder
- [ ] Redirección a login si no autenticado
- [ ] Token se envía en headers

### Datos
- [ ] API endpoints responden correctamente
- [ ] Datos se mapean a componentes correctamente
- [ ] No hay errores de tipos

---

## ⚡ Performance

### Dashboard
- [ ] Carga < 2 segundos
- [ ] Auto-refresh no causa lag
- [ ] No memory leaks en dev tools

### Notificaciones
- [ ] Carga < 1.5 segundos
- [ ] Auto-refresh < 100ms
- [ ] Scroll suave en lista larga

### Webhooks
- [ ] Carga < 2 segundos
- [ ] Expansión de logs suave
- [ ] Eliminación inmediata en UI

---

## 🔒 Seguridad

- [ ] No hay XSS vulnerabilities (revisar innerHTML)
- [ ] Data sensitiva no se loguea
- [ ] Confirmaciones para acciones destructivas
- [ ] No hay hardcodes de URLs

---

## 📊 Accesibilidad (a18y)

### Dashboard
- [ ] Título de página correcto
- [ ] ARIA labels en botones
- [ ] Contraste de colores es suficiente
- [ ] Keyboard navigation funciona

### Notificaciones
- [ ] Tab navigation funciona
- [ ] Screen reader describe elementos
- [ ] Filtros son accesibles

### Webhooks
- [ ] Tabla es accesible
- [ ] Botones de acción tienen labels
- [ ] Modal de confirmación es accesible

---

## 📋 Test Manual Detallado

### Escenario 1: Usuario nuevo en Dashboard
1. [ ] Navega a `/admin/dashboard`
2. [ ] Ve spinner de carga
3. [ ] Datos aparecen
4. [ ] Empresas recientes se muestran
5. [ ] Actualiza manualmente
6. [ ] Espera 30 segundos para auto-refresh

### Escenario 2: Usuario revisa Notificaciones
1. [ ] Navega a `/admin/notifications`
2. [ ] Ve lista de notificaciones
3. [ ] Filtra por "Sin leer"
4. [ ] Click en una sin leer
5. [ ] Se marca como leída
6. [ ] Contador disminuye
7. [ ] Click en "Marcar todas como leídas"

### Escenario 3: Usuario gestiona Webhooks
1. [ ] Navega a `/admin/webhooks`
2. [ ] Ve lista de webhooks
3. [ ] Clickea en un webhook para ver logs
4. [ ] Expande un log
5. [ ] Ve payload y respuesta
6. [ ] Clickea botón "Probar"
7. [ ] Ve resultado del test
8. [ ] Clickea "Eliminar"
9. [ ] Confirma eliminación

---

## 🐛 Bugs Conocidos / Pendientes

- [ ] WebhookForm no implementado (próxima fase)
- [ ] Gráficos en Dashboard (Recharts - opcional)
- [ ] Export de notificaciones (futuro)
- [ ] Paginación en Webhooks (si hay muchos)

---

## ✅ Sign-off

| Componente | Testeado | Status | Fecha | Responsable |
|-----------|----------|--------|-------|------------|
| Dashboard | [ ] | — | — | — |
| Notificaciones | [ ] | — | — | — |
| Webhooks | [ ] | — | — | — |

---

**Próximo paso:** Ejecutar este checklist y reportar cualquier issue.
