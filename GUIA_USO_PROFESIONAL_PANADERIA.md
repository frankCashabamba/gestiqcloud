# 🥖 Guía de Uso Profesional - Panadería con GestiQCloud

**Fecha**: Enero 2025  
**Versión**: 1.0.0  
**Para**: Panaderías profesionales

---

## 🎯 Flujo de Trabajo Diario

### Mañana (Inicio del Día)

#### 1. Importar Registro del Día (5 minutos)
```
1. Abrir http://localhost:5173/panaderia/importador
2. Seleccionar archivo Excel (ej: 22-10-2025.xlsx)
3. Verificar fecha detectada o ingresarla manualmente
4. Marcar "Simular ventas" ✓
5. Click "Importar Archivo"
```

**Qué hace el sistema**:
- ✅ Crea 283 productos (si no existen)
- ✅ Registra inventario diario histórico
- ✅ **Inicializa stock real** con CANTIDAD del Excel
- ✅ Registra ventas históricas como movimientos
- ✅ Calcula automáticamente ajustes

**Resultado**: Stock del día listo en el sistema ✅

---

#### 2. Abrir Turno en POS (1 minuto)
```
1. Ir a http://localhost:5173/pos
2. Sección "Gestión de Turno"
3. Fondo Inicial: 100.00 € (o lo que tengas en caja)
4. Click "Abrir Turno"
```

**Estado**: 🟢 Turno Abierto - Listo para vender

---

### Durante el Día (Ventas)

#### 3. Vender desde el POS (30 segundos por venta)
```
1. Ir a http://localhost:5173/pos/nuevo-ticket
2. Buscar producto (nombre o código)
3. Añadir líneas (qty +/-)
4. Click "Cobrar"
5. Seleccionar método: Efectivo/Tarjeta/Vale
6. Confirmar cobro
```

**Qué hace el sistema automáticamente**:
- ✅ Crea ticket en `pos_receipts`
- ✅ Crea movimiento en `stock_moves` (kind='sale', qty=-X)
- ✅ **Actualiza stock_items** (resta lo vendido)
- ✅ Si BOM activo: ejecuta backflush (consume MP)
- ✅ Genera número de ticket único

**Resultado**: Stock actualizado en tiempo real ✅

---

### Noche (Cierre del Día)

#### 4. Cerrar Turno (2 minutos)
```
1. Contar efectivo en caja
2. En POS Dashboard → "Gestión de Turno"
3. Total de Cierre: 1,234.56 € (lo que contaste)
4. Click "Cerrar Turno"
```

**Qué hace el sistema**:
- ✅ Registra cierre de caja
- ✅ Calcula diferencia vs ventas
- ✅ Bloquea nuevas ventas en ese turno

---

#### 5. Revisar Stock Final (3 minutos)
```
1. Ir a http://localhost:5173/inventario
2. Ver stock actual de cada producto
3. Comparar con stock físico
```

**Si hay diferencias**:
```
1. Ir a http://localhost:5173/inventario/ajustes
2. Crear ajuste (+ entrada, - salida)
3. Motivo: "Merma pan del día", "Rotura", etc.
```

**Sistema registra**: Ajuste en `stock_moves` (kind='adjustment')

---

## 📊 Flujo de Datos Completo

```
MAÑANA:
Excel 22-10-2025.xlsx
  CANTIDAD = 100 panes
       ↓
[IMPORTAR]
       ↓
stock_items.qty = 100  ← Stock real inicializado
daily_inventory (registro histórico)

MEDIODÍA:
POS vende 5 panes
       ↓
stock_moves (kind='sale', qty=-5)
       ↓
stock_items.qty = 95  ← Stock actualizado automático

NOCHE:
Cierre de caja
       ↓
Stock físico = 93 panes (encontraste 2 rotos)
       ↓
Crear ajuste: -2 (merma)
       ↓
stock_items.qty = 93  ← Stock corregido
       ↓
✅ Stock real = Stock físico
```

---

## 🎯 Tablas del Sistema (No Duplicadas)

### Tabla: `products` (Catálogo)
**Qué es**: Productos disponibles (Pan, Empanada, etc.)  
**Actualiza**: Importador (nuevos) + Manual  
**Lee**: POS, Inventario, Ventas

### Tabla: `stock_items` (Stock REAL)
**Qué es**: Cantidad actual en almacén **AHORA**  
**Actualiza**: 
- Importador (inicializa con CANTIDAD)
- POS ventas (resta automático)
- Compras (suma)
- Ajustes manuales  
**Lee**: POS (para saber si hay stock), Inventario, Reportes

### Tabla: `stock_moves` (Historial Movimientos)
**Qué es**: Registro de TODAS las entradas/salidas  
**Tipos**:
- `opening_balance` - Importador (stock inicial)
- `sale` - POS vende / Histórico del Excel
- `purchase` - Compras a proveedores
- `adjustment` - Ajustes manuales (merma, rotura)
- `consume` - Backflush (consume MP)  
**Actualiza**: Automático (triggers)  
**Lee**: Kardex, Reportes, Auditoría

### Tabla: `daily_inventory` (Registro Histórico Excel)
**Qué es**: Copia exacta del Excel (auditoría)  
**Actualiza**: Solo importador (1 vez al día)  
**Lee**: Reportes históricos, Comparativas

### Tabla: `pos_receipts` (Tickets POS)
**Qué es**: Tickets de venta del mostrador  
**Actualiza**: POS  
**Lee**: Cierre de caja, Historial, Facturación

### Tabla: `invoices` (Facturas Legales)
**Qué es**: Facturas con NIF/RUC (B2B)  
**Actualiza**: POS→Factura (botón convertir)  
**Lee**: Contabilidad, E-factura

---

## 📈 Reportes Disponibles

### 1. Inventario Diario (Histórico)
```
http://localhost:5173/panaderia/inventario
```
- Stock inicial del día
- Ventas del día
- Stock final del día
- Ajustes detectados
- KPIs: total ventas, ingresos, ajustes

### 2. Stock Actual (Tiempo Real)
```
http://localhost:5173/inventario
```
- Cantidad actual de cada producto
- Por almacén
- Highlight stock bajo (< 10)
- Lotes y caducidad

### 3. Movimientos (Kardex)
```
http://localhost:5173/inventario/movimientos
```
- Historial completo de movimientos
- Por tipo (venta, compra, ajuste)
- Trazabilidad completa

### 4. Ventas del Día (POS)
```
http://localhost:5173/pos/historial
```
- Todos los tickets del día
- Estados (draft, paid, invoiced)
- Totales por turno

---

## 🔄 Escenarios Comunes

### Escenario 1: Día Normal
```
1. 8:00 AM - Importar Excel del día
   → Stock inicializado: 100 panes

2. 8:30 AM - Abrir turno (fondo: 50€)
   → Turno #123 abierto

3. 9:00-20:00 - Ventas normales en POS
   → 85 panes vendidos
   → Stock actual: 15 panes

4. 20:30 PM - Cerrar turno (total: 892€)
   → Turno cerrado

5. 21:00 PM - Recuento físico: 15 panes
   → ✅ Sin diferencias (stock = físico)
```

### Escenario 2: Con Mermas
```
1. Importar Excel → Stock: 100 panes
2. POS vende → 85 panes
3. Stock sistema: 15 panes
4. Recuento físico: 12 panes (3 rotos)
5. Crear ajuste: -3 "Merma pan del día"
6. Stock final: 12 panes ✅
```

### Escenario 3: Compra de MP
```
1. Recibo 50kg harina
2. Ir a http://localhost:5173/panaderia/compras
3. Crear compra:
   - Proveedor: Molinos SA
   - Producto: Harina
   - Cantidad: 50 kg
   - Costo: 1.20€/kg
4. Sistema crea:
   - Registro en purchase
   - stock_move (kind='purchase', qty=+50)
   - Actualiza stock_items harina
```

### Escenario 4: Backflush Automático
```
Prerequisito: BOM creada para "Pan Tapado"
- Harina: 0.0378 kg
- Huevo: 0.0583 un
- Manteca: 0.0005 kg

1. POS vende 10 Pan Tapado
2. Si BACKFLUSH_ENABLED=1:
   → Descuenta automático:
     - Harina: -0.378 kg
     - Huevo: -0.583 un
     - Manteca: -0.005 kg
   → Crea stock_moves (kind='consume')
   → Actualiza stock_items MP
```

---

## 🎓 Buenas Prácticas

### Stock Inicial
- ✅ **Importar Excel cada mañana** (stock del día)
- ✅ Usar CANTIDAD como stock disponible para vender
- ✅ Sistema registra automáticamente las ventas históricas

### Durante el Día
- ✅ Todas las ventas por POS (actualiza stock automático)
- ✅ Si vendes fuera del POS, crear ajuste manual
- ✅ Revisar stock en tiempo real si dudas

### Cierre
- ✅ Cerrar turno con total real contado
- ✅ Hacer recuento físico de productos clave
- ✅ Ajustar diferencias inmediatamente
- ✅ Revisar movimientos del día

### BOM (Opcional)
- ✅ Crear BOM de tus productos principales
- ✅ Activar backflush: `BACKFLUSH_ENABLED=1`
- ✅ El sistema consume MP automáticamente
- ✅ Control de mermas y costos real

---

## 📋 Checklist Pre-Operación

### Setup Inicial (1 vez)
- [ ] Aplicar migraciones: `python scripts/py/bootstrap_imports.py --dir ops/migrations`
- [ ] Crear almacén por defecto: `python scripts/create_default_warehouse.py <TENANT_UUID>`
- [ ] Verificar backend: `docker logs backend | grep "router mounted"`
- [ ] Verificar frontend: `http://localhost:5173/panaderia`
- [ ] Crear usuario cajero
- [ ] Configurar impresora (si tienes)

### Operación Diaria
- [ ] Importar Excel del día
- [ ] Verificar stock inicializado (inventario)
- [ ] Abrir turno en POS
- [ ] Realizar ventas
- [ ] Cerrar turno
- [ ] Hacer recuento físico
- [ ] Ajustar diferencias

---

## 🔧 Comandos de Administración

### Ver Stock Actual (SQL)
```sql
docker exec -it db psql -U postgres -d gestiqclouddb_dev

-- Stock de todos los productos
SELECT 
  p.name,
  si.qty as stock_actual,
  w.name as almacen
FROM stock_items si
JOIN products p ON p.id = si.product_id
JOIN warehouses w ON w.id = si.warehouse_id
WHERE si.tenant_id = 'TU-UUID'::uuid
ORDER BY p.name;
```

### Ver Movimientos del Día
```sql
SELECT 
  p.name as producto,
  sm.kind as tipo,
  sm.qty,
  sm.created_at
FROM stock_moves sm
JOIN products p ON p.id = sm.product_id
WHERE sm.tenant_id = 'TU-UUID'::uuid
  AND sm.created_at::date = CURRENT_DATE
ORDER BY sm.created_at DESC;
```

### Comparar Stock Excel vs Real
```sql
SELECT 
  p.name,
  di.stock_final as esperado_excel,
  si.qty as stock_real,
  (si.qty - di.stock_final) as diferencia
FROM daily_inventory di
JOIN products p ON p.id = di.product_id
JOIN stock_items si ON si.product_id = di.product_id
WHERE di.tenant_id = 'TU-UUID'::uuid
  AND di.fecha = '2025-10-22'
  AND (si.qty - di.stock_final) != 0;
```

---

## 📊 KPIs Disponibles

### Dashboard Panadería
- Ventas totales (unidades)
- Ingresos totales (€)
- Compras del mes (€)
- Leche recibida (litros)

### Inventario Diario
- Total registros importados
- Unidades vendidas
- Ingresos totales
- Registros con ajuste (%)

### Stock Actual
- Productos en stock
- Productos con stock bajo
- Valor total inventario
- Movimientos del día

---

## 🚨 Troubleshooting

### Problema: "No default warehouse"
**Solución**:
```bash
python scripts/create_default_warehouse.py <TU-TENANT-UUID>
```

### Problema: "Stock no se actualiza al vender"
**Verificar**:
1. ¿El turno está abierto?
2. ¿El ticket se marcó como "paid"?
3. Ver `stock_moves` - debe haber movimiento kind='sale'

**SQL Debug**:
```sql
SELECT * FROM stock_moves
WHERE product_id = <PRODUCT_ID>
ORDER BY created_at DESC
LIMIT 10;
```

### Problema: "Diferencias entre stock físico y sistema"
**Es normal**: Mermas, roturas, robos

**Solución**:
```
1. Ir a /inventario/ajustes
2. Crear ajuste con la diferencia
3. Motivo: "Recuento físico - merma"
```

### Problema: "El Excel no detecta la fecha"
**Verificar nombre**: dd-mm-aaaa.xlsx (ej: 22-10-2025.xlsx)

**Alternativa**: Usar "Fecha Manual" en el importador

---

## 🎓 Tips Profesionales

### 1. Importación Diaria
- Mantén formato consistente del Excel
- Usa fecha en el nombre: `22-10-2025.xlsx`
- Verifica que CANTIDAD = stock del día (antes de abrir)

### 2. POS Eficiente
- Atajos: Enter para cobrar, Esc para cancelar
- Escanea códigos (si tienes lector)
- Mantén productos favoritos arriba

### 3. Control de Stock
- Revisa inventario en tiempo real durante el día
- Haz recuento físico al cierre
- Ajusta diferencias inmediatamente
- Identifica patrones de mermas

### 4. BOM y Backflush
- Crea BOM de productos principales (Pan Tapado, etc.)
- Activa backflush cuando esté listo
- Monitorea consumo de MP vs ventas
- Detecta desperdicios o robos de ingredientes

### 5. Reportes
- Exporta inventario diario a Excel mensualmente
- Compara ventas POS vs registro histórico
- Analiza productos con más ajustes (mermas)
- Identifica productos de alta rotación

---

## 📱 Uso en Tablet

### Setup Tablet
```
1. Conectar tablet a la misma red WiFi
2. Obtener IP del servidor: ipconfig (Windows) o ifconfig (Linux)
3. En tablet, abrir Chrome
4. Ir a http://<IP-SERVIDOR>:5173/pos
   Ejemplo: http://192.168.1.100:5173/pos
```

### Instalar como App
```
1. Chrome → Menú (3 puntos)
2. "Añadir a pantalla de inicio"
3. Confirmar
4. Ahora tienes app nativa
```

### Offline
- Sistema funciona sin internet (offline-lite)
- Ventas se encolan
- Al reconectar, sincroniza automático

---

## 🔐 Seguridad y Roles

### Roles Recomendados

#### Cajero (Operario)
**Puede**:
- Abrir/cerrar turno (si tiene permiso)
- Crear tickets
- Cobrar ventas
- Ver historial de su turno

**No puede**:
- Modificar precios (sin permiso)
- Eliminar tickets
- Acceder a configuración
- Ver datos de otros turnos

#### Gerente (Manager)
**Puede**:
- Todo lo del cajero
- Ver todos los turnos
- Crear ajustes de inventario
- Importar Excel
- Ver reportes completos
- Gestionar usuarios
- Devoluciones sin ticket

#### Admin (Owner)
**Puede**:
- Todo lo del gerente
- Configurar e-factura
- Gestionar pagos online
- Configurar certificados
- Acceso completo

---

## 🎯 Métricas de Éxito

### Operativas
- ✅ Importación diaria en < 2 min
- ✅ Venta en POS < 30 seg
- ✅ Stock actualizado en tiempo real
- ✅ Diferencias stock < 2%
- ✅ Cierre de caja < 5 min

### Negocio
- ✅ Datos históricos completos
- ✅ Trazabilidad total (quién, cuándo, qué)
- ✅ Decisiones basadas en datos
- ✅ Detección de mermas y robos
- ✅ Control de costos (con BOM)

---

## 📞 Soporte

### Documentación
- **INTEGRACION_EXCEL_ERP_CORRECTA.md** - Arquitectura de datos
- **SPEC1_QUICKSTART.md** - Setup rápido
- **AGENTS.md** - Arquitectura completa

### Comandos Útiles
```bash
# Ver logs
docker logs -f backend

# Ver DB
docker exec -it db psql -U postgres -d gestiqclouddb_dev

# Reiniciar todo
docker compose restart
```

---

## ✅ Conclusión

**Sistema Completo Integrado**:
- Excel → Inicializa stock real ✅
- POS → Actualiza stock automático ✅
- Inventario → Control en tiempo real ✅
- Sin duplicación de datos ✅
- Trazabilidad completa ✅

**Listo para uso profesional** 🚀

---

**Versión**: 1.0  
**Soporte**: GestiQCloud Team  
**Fecha**: Enero 2025

🥖 **¡Buena suerte con tu panadería!**
