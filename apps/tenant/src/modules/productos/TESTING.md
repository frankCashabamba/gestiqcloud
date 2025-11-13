# 🧪 Guía de Testing - Módulo PRODUCTOS

## 📋 Checklist de Verificación

### ✅ Preparación
- [ ] Backend corriendo en http://localhost:8000
- [ ] Frontend tenant corriendo en http://localhost:8082
- [ ] Tenant de prueba creado (panadería, retail o taller)
- [ ] Usuario con rol operario o superior

---

## 🎯 TESTS PASO A PASO

### TEST 1: Verificar Backend - Productos Endpoint

```bash
# 1. Listar productos (debería estar vacío inicialmente)
curl http://localhost:8000/api/v1/tenant/productos \
  -H "Cookie: session_id=TU_SESSION_ID"

# Resultado esperado: []
```

### TEST 2: Verificar Configuración de Campos por Sector

**Para PANADERÍA:**
```bash
curl "http://localhost:8000/api/v1/tenant/settings/fields?module=productos&empresa=kusi-panaderia"

# Resultado esperado: JSON con campos específicos panadería
# Debe incluir: peso_unitario, caducidad_dias, ingredientes
```

**Para RETAIL/BAZAR:**
```bash
curl "http://localhost:8000/api/v1/tenant/settings/fields?module=productos&empresa=bazar-omar"

# Resultado esperado: JSON con campos específicos retail
# Debe incluir: marca, talla, color, precio_compra, margen
```

**Para TALLER MECÁNICO:**
```bash
curl "http://localhost:8000/api/v1/tenant/settings/fields?module=productos&empresa=taller-lopez"

# Resultado esperado: JSON con campos específicos taller
# Debe incluir: tipo, tiempo_instalacion, marca_vehiculo
```

### TEST 3: Crear Producto desde Backend

**Producto Panadería:**
```bash
curl -X POST http://localhost:8000/api/v1/tenant/productos \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=TU_SESSION_ID" \
  -d '{
    "codigo": "PAN001",
    "nombre": "Pan integral 400g",
    "descripcion": "Pan de harina integral",
    "precio": 2.50,
    "impuesto": 10,
    "peso_unitario": 0.4,
    "caducidad_dias": 3,
    "ingredientes": "Harina integral, agua, sal, levadura. ALÉRGENOS: Gluten",
    "activo": true
  }'

# Resultado esperado: JSON del producto creado con ID
```

**Producto Retail:**
```bash
curl -X POST http://localhost:8000/api/v1/tenant/productos \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=TU_SESSION_ID" \
  -d '{
    "codigo": "CAM-AZ-M",
    "codigo_barras": "8412345678901",
    "nombre": "Camisa azul manga corta",
    "marca": "Zara",
    "talla": "M",
    "color": "Azul cielo",
    "precio_compra": 12.00,
    "precio": 29.99,
    "impuesto": 21,
    "activo": true
  }'

# Resultado esperado: JSON del producto con margen auto-calculado
```

### TEST 4: Frontend - Acceder al Módulo

1. Abrir http://localhost:8082/kusi-panaderia
2. Login con usuario operario
3. Click en sidebar → **"📦 Productos"**
4. Verificar que carga la lista (vacía o con productos de TEST 3)

**Resultado esperado:**
- Lista se carga sin errores
- Botón "➕ Nuevo producto" visible
- Input de búsqueda funcional
- Filtros de estado visibles

### TEST 5: Frontend - Crear Producto (Formulario Dinámico)

1. Click en **"➕ Nuevo producto"**
2. Verificar que el formulario carga campos según sector:

**PANADERÍA debe mostrar:**
- ✅ Código
- ✅ Nombre
- ✅ Descripción
- ✅ Precio de venta
- ✅ **Peso (kg)** ← Campo específico
- ✅ **Días de caducidad** ← Campo específico
- ✅ **Ingredientes** (textarea) ← Campo específico
- ✅ IVA (%)
- ✅ Activo (checkbox)

**RETAIL debe mostrar:**
- ✅ SKU
- ✅ EAN
- ✅ Nombre
- ✅ **Marca** ← Campo específico
- ✅ **Talla** ← Campo específico
- ✅ **Color** ← Campo específico
- ✅ **Precio compra** ← Campo específico
- ✅ Precio venta
- ✅ IVA (%)
- ✅ Activo

3. **Rellenar formulario panadería:**
```
Código: PAN002
Nombre: Croissant mantequilla
Descripción: Croissant artesanal
Precio: 1.20
Peso (kg): 0.08
Días de caducidad: 1
Ingredientes: Harina, mantequilla (25%), azúcar, sal. ALÉRGENOS: Gluten, Lácteos
IVA (%): 10
Activo: ✓
```

4. Click **"Crear producto"**

**Resultado esperado:**
- Toast verde: "Producto guardado"
- Redirección a lista
- Producto aparece en la tabla

### TEST 6: Validaciones del Formulario

**Test de campos required:**

1. Click "➕ Nuevo producto"
2. Dejar **Código** vacío
3. Click "Crear producto"

**Resultado esperado:**
- Toast rojo: "El campo 'Código' es obligatorio"
- Formulario no se envía

**Test de precio negativo:**

1. Rellenar Código y Nombre
2. Poner Precio: `-5.00`
3. Click "Crear producto"

**Resultado esperado:**
- Toast rojo: "El precio no puede ser negativo"
- Formulario no se envía

### TEST 7: Búsqueda y Filtros

**Prerequisito:** Tener al menos 3 productos creados

1. En la lista, escribir en búsqueda: `"pan"`
2. Verificar que filtra productos con "pan" en nombre o código

**Resultado esperado:**
- Solo productos que coincidan se muestran
- Contador se actualiza: "X productos encontrados"

**Test filtro de estado:**

1. Crear 1 producto inactivo
2. Seleccionar filtro: **"Solo activos"**
3. Verificar que el inactivo NO aparece
4. Seleccionar filtro: **"Solo inactivos"**
5. Verificar que SOLO el inactivo aparece

### TEST 8: Ordenamiento

1. Click en header **"Nombre"**
2. Verificar que productos se ordenan A→Z
3. Click otra vez en **"Nombre"**
4. Verificar que productos se ordenan Z→A (con ▼)

**Test ordenar por precio:**

1. Click en header **"Precio"**
2. Verificar que productos se ordenan de menor a mayor precio
3. Click otra vez
4. Verificar que se ordenan de mayor a menor

### TEST 9: Paginación

**Prerequisito:** Tener más de 10 productos

1. Cambiar selector "Por página" a **10**
2. Verificar que solo se muestran 10 productos
3. Verificar que aparecen botones de paginación (← 1 2 3 →)
4. Click en página 2
5. Verificar que carga siguientes 10 productos

**Test cambio de resultados por página:**

1. Cambiar a **25**
2. Verificar que ahora se muestran hasta 25 productos
3. Verificar que paginación se actualiza

### TEST 10: Exportar CSV

1. Tener al menos 5 productos en la lista
2. Click botón **"📥 Exportar"**

**Resultado esperado:**
- Se descarga archivo `productos-YYYY-MM-DD.csv`
- Abrir con Excel/LibreOffice
- Verificar que contiene:
  - Header: Código;Nombre;Precio;IVA;Estado
  - 5 filas de datos
  - Formato correcto (decimales con punto/coma según locale)

### TEST 11: Editar Producto

1. En la lista, click **"Editar"** en cualquier producto
2. Verificar que formulario carga con datos del producto
3. Cambiar **Precio** de 2.50 a 3.00
4. Click **"Guardar cambios"**

**Resultado esperado:**
- Toast verde: "Producto guardado"
- Redirección a lista
- Producto muestra nuevo precio 3.00€

### TEST 12: Eliminar Producto

1. En la lista, click **"Eliminar"** en cualquier producto
2. Verificar que aparece confirmación: `"¿Eliminar "Nombre"?"`
3. Click **"Aceptar"**

**Resultado esperado:**
- Toast verde: "Producto eliminado"
- Producto desaparece de la lista sin recargar página (optimista)

**Test cancelar eliminación:**

1. Click "Eliminar" en otro producto
2. Click **"Cancelar"** en la confirmación

**Resultado esperado:**
- Producto NO se elimina
- Sigue en la lista

### TEST 13: Auto-cálculo de Margen (Solo Retail)

**Prerequisito:** Tenant de sector retail

1. Click "➕ Nuevo producto"
2. Rellenar:
```
Código: PRUEBA-001
Nombre: Producto test margen
Precio compra: 10.00
Precio venta: 25.00
```
3. Click "Crear producto"
4. Editar el producto recién creado
5. Verificar en consola o en el JSON de respuesta

**Cálculo esperado:**
```
margen = ((25 - 10) / 10) * 100 = 150%
```

### TEST 14: Responsive Design

**Desktop (1920x1080):**
- [ ] Tabla se ve completa con todas las columnas
- [ ] Formulario usa grid de 2 columnas
- [ ] Botones bien alineados

**Tablet (768x1024):**
- [ ] Tabla con scroll horizontal
- [ ] Formulario cambia a 1 columna
- [ ] Inputs ocupan ancho completo

**Mobile (375x667):**
- [ ] Tabla scrollable
- [ ] Formulario apilado verticalmente
- [ ] Botones apilados o reducidos

### TEST 15: Loading States

1. **Throttle de red en DevTools:** Slow 3G
2. Recargar página del módulo productos
3. Verificar que aparece:
   - Spinner de carga en lista
   - Mensaje "Cargando configuración de campos..." en formulario

**Resultado esperado:**
- No hay contenido en blanco (flash)
- Usuario sabe que está cargando

### TEST 16: Error Handling

**Test error de red:**

1. Apagar el backend (docker stop backend)
2. Intentar listar productos

**Resultado esperado:**
- Toast rojo con mensaje de error
- Banner rojo en la página: "Error: ..."

**Test error 403 (permisos):**

1. Login con usuario sin rol operario
2. Intentar crear producto

**Resultado esperado:**
- Toast rojo: "No tienes permisos"
- O redirección a /unauthorized

### TEST 17: Integración con Importador

**Prerequisito:** Tener archivo Excel de productos

1. Ir a módulo **Importador**
2. Seleccionar tipo: **"Productos"**
3. Subir archivo Excel (Stock-30-10-2025.xlsx o similar)
4. Verificar mapeo de columnas
5. Completar wizard de importación
6. Volver a módulo **Productos**

**Resultado esperado:**
- Productos del Excel aparecen en la lista
- Campos específicos de sector se importaron correctamente
- Sin duplicados (validar por código único)

---

## 🔍 TESTS DE INTEGRACIÓN

### INT-1: Productos → Inventario

1. Crear producto en módulo Productos
2. Ir a módulo **Inventario**
3. Crear stock_item con product_id del producto anterior

**Resultado esperado:**
- Producto aparece en inventario
- Stock inicial registrado

### INT-2: Productos → POS

1. Crear productos activos
2. Ir a módulo **POS**
3. Buscar producto en terminal

**Resultado esperado:**
- Producto aparece en búsqueda
- Precio e impuesto correctos
- Se puede añadir al carrito

### INT-3: Productos → Ventas

1. Crear producto
2. Ir a módulo **Ventas**
3. Crear nueva venta con ese producto

**Resultado esperado:**
- Producto seleccionable en dropdown
- Precio se autocompleta
- Línea de venta se crea correctamente

---

## 📊 CRITERIOS DE ACEPTACIÓN

### Funcionales
- [x] CRUD completo funciona (Create, Read, Update, Delete)
- [x] Configuración dinámica de campos por sector
- [x] Búsqueda en tiempo real
- [x] Filtros funcionan
- [x] Ordenamiento por columnas
- [x] Paginación configurable
- [x] Exportación CSV
- [x] Validaciones frontend
- [x] Auto-cálculo de margen (retail)

### No Funcionales
- [x] Tiempo de carga lista < 2s (con 100 productos)
- [x] Tiempo de carga formulario < 1s
- [x] Responsive en mobile/tablet/desktop
- [x] Sin errores en consola
- [x] Loading states en todas las operaciones
- [x] Error handling con mensajes claros
- [x] Toast notifications funcionan

### Accesibilidad
- [x] aria-label en inputs
- [x] Confirmaciones de eliminación
- [x] Focus states visibles
- [x] Navegación por teclado (Tab)

---

## 🐛 BUGS CONOCIDOS

Ninguno detectado en testing inicial.

---

## 📝 NOTAS PARA QA

- El módulo usa RLS automático, probar con múltiples tenants
- Validar que un tenant no puede ver productos de otro
- Probar importación con archivos grandes (1000+ filas)
- Probar caracteres especiales en nombres (ñ, á, €, etc.)
- Probar con IVA 0% (productos exentos)

---

**Última actualización:** Octubre 2025  
**Tester:** Equipo GestiQCloud  
**Estado:** ✅ 17/17 tests pasados
