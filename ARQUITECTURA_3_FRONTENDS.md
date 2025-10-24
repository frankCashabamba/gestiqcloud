# Arquitectura Correcta - 1 Backend + 3 Frontends

## 🏗️ Estructura del Sistema

```
┌─────────────────────────────────────────────────────┐
│           BACKEND ÚNICO (Puerto 8000)               │
│           FastAPI + PostgreSQL + Redis              │
│                /api/v1/*                            │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   ADMIN     │ │   TENANT    │ │   TPV       │
│  :8082      │ │   :8081     │ │  :8083      │
│             │ │             │ │             │
│ Gestión     │ │ Backoffice  │ │ Punto       │
│ Global      │ │ Empresa     │ │ de Venta    │
│             │ │             │ │             │
│ - Tenants   │ │ - Módulos   │ │ - Grid      │
│ - Config    │ │ - Reports   │ │   Productos │
│ - Monitoreo │ │ - Forms     │ │ - Touch     │
│             │ │ - Settings  │ │ - Offline   │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## 🎯 Propósito de Cada Frontend

### Admin (Puerto 8082)
**Para**: Super Admin / Owner  
**Funciones**:
- Crear/gestionar tenants
- Monitoreo global
- Configuración sistema
- Ver todos los datos

**Usuarios**: Administradores del SaaS

---

### Tenant (Puerto 8081)
**Para**: Gerente / Manager / Backoffice  
**Funciones**:
- Todos los módulos (Panadería, Inventario, etc.)
- Reportes y análisis
- Configuración del negocio
- Gestión de usuarios
- Importador Excel
- E-factura
- Pagos online

**Usuarios**: Gerentes, contables, administradores de la panadería

---

### TPV (Puerto 8083) - **NUEVO** ✨
**Para**: Cajeros / Vendedores  
**Funciones**:
- **SOLO VENDER** (interfaz ultra-simple)
- Grid de productos con fotos grandes
- Click → añade al carrito
- Cobrar (efectivo, tarjeta)
- **Offline total** (IndexedDB + sync)
- **Touch-optimized** (botones grandes)
- **Sin menús** complejos

**Usuarios**: Cajeros en el mostrador

**Diseño**: Tipo kiosco/tablet, fullscreen, touch-friendly

---

## 📱 Nueva App TPV

### Estructura
```
apps/tpv/                    # ✨ NUEVO
├── src/
│   ├── components/
│   │   ├── ProductGrid.tsx      # Grid de productos (mosaico)
│   │   ├── Cart.tsx             # Carrito lateral
│   │   ├── PaymentScreen.tsx   # Pantalla de cobro
│   │   └── OfflineIndicator.tsx # Estado conexión
│   ├── services/
│   │   ├── api.ts               # Llamadas backend
│   │   ├── offline.ts           # IndexedDB + sync
│   │   └── products.ts          # Cache productos
│   ├── db/
│   │   └── schema.ts            # PGlite/IndexedDB schema
│   ├── App.tsx                  # App principal (sin router)
│   └── main.tsx
├── public/
│   └── manifest.json            # PWA manifest
├── package.json
├── vite.config.ts
├── Dockerfile
└── nginx.conf
```

---

## 🎨 UI del TPV (Diseño)

### Pantalla Principal
```
┌─────────────────────────────────────────────────┐
│ 🥖 Mi Panadería          📡 Online    👤 Juan  │ ← Header simple
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    │
│  │ 🥖  │ │ 🥐  │ │ 🧁  │ │ 🍰  │ │ 🥧  │    │
│  │ Pan │ │Crois│ │Muff│ │Tarta│ │ Pie │    │
│  │1.50€│ │2.00€│ │1.80│ │15.0│ │12.0│    │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    │
│                                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    │ ← Grid 
│  │ ... │ │ ... │ │ ... │ │ ... │ │ ... │    │   productos
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    │
│                                                 │
├─────────────────────────────────────────────────┤
│ 🛒 CARRITO (3 items)              TOTAL: 5.30€ │ ← Footer carrito
│ [Ver Carrito] [Cobrar]                         │
└─────────────────────────────────────────────────┘
```

### Click en Producto
- ✅ Añade al carrito (qty +1)
- ✅ Vibración táctil (si móvil)
- ✅ Animación feedback
- ✅ Sin confirmación (rápido)

### Carrito Lateral
```
┌─────────────────┐
│ 🛒 CARRITO      │
├─────────────────┤
│ Pan x3   4.50€  │ ← Click para editar qty
│ Croissant x1 2€ │
│ Muffin x2  3.60€│
├─────────────────┤
│ Subtotal  10.10€│
│ IVA 10%    1.01€│
│ TOTAL    11.11€ │
├─────────────────┤
│ [Vaciar]        │
│ [COBRAR] ←Grande│
└─────────────────┘
```

---

## 🚀 Creación del TPV

### Estructura del Proyecto
```bash
apps/
├── admin/        # Puerto 8082 (React - gestión global)
├── tenant/       # Puerto 8081 (React - backoffice empresa)
└── tpv/          # Puerto 8083 (React - punto venta) ✨ NUEVO
    ├── src/
    │   ├── components/
    │   │   ├── ProductGrid.tsx
    │   │   ├── ProductCard.tsx
    │   │   ├── Cart.tsx
    │   │   ├── CartItem.tsx
    │   │   ├── PaymentScreen.tsx
    │   │   └── OfflineIndicator.tsx
    │   ├── services/
    │   │   ├── api.ts          # Llamadas a :8000/api/v1
    │   │   ├── offline.ts      # IndexedDB
    │   │   └── sync.ts         # Background sync
    │   ├── db/
    │   │   ├── schema.ts       # IndexedDB schema
    │   │   └── operations.ts   # CRUD local
    │   ├── hooks/
    │   │   ├── useProducts.ts  # Cache productos
    │   │   ├── useCart.ts      # Estado carrito
    │   │   └── useOffline.ts   # Estado online/offline
    │   ├── App.tsx
    │   ├── main.tsx
    │   └── sw.ts               # Service Worker
    ├── public/
    │   ├── manifest.json
    │   └── icons/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── Dockerfile
    └── nginx.conf
```

---

## 🎨 Features del TPV

### Diseño
- ✅ Fullscreen (sin chrome del navegador)
- ✅ Grid de productos (4-6 columnas)
- ✅ Cards grandes con imagen
- ✅ Precio destacado
- ✅ Touch-optimized (min 44px botones)
- ✅ Sin scroll innecesario
- ✅ Modo oscuro opcional

### Funcionalidad
- ✅ Click producto → añade carrito
- ✅ Carrito lateral flotante
- ✅ Editar qty inline (+ / -)
- ✅ Eliminar items
- ✅ Calcular IVA automático
- ✅ Cobro efectivo/tarjeta
- ✅ Imprimir ticket (window.print)

### Offline
- ✅ Cache productos local (IndexedDB)
- ✅ Ventas encolan si offline
- ✅ Sync automático al reconectar
- ✅ Indicador de estado (🔴 offline / 🟢 online)
- ✅ No pierde ventas nunca

### Performance
- ✅ Lazy loading imágenes
- ✅ Virtual scrolling (si muchos productos)
- ✅ Debounce búsqueda
- ✅ Optimistic UI
- ✅ Cache agresivo

---

## 🔌 Integración Backend

### Endpoints que Usa TPV
```
GET  /api/v1/products          # Catálogo (cache 1h)
GET  /api/v1/pos/shifts/current/{register_id}
POST /api/v1/pos/receipts      # Crear venta
POST /api/v1/pos/receipts/{id}/pay
GET  /api/v1/inventory/stock   # Stock disponible
```

### Headers
```
X-Tenant-ID: <UUID>
Authorization: Bearer <token-cajero>
```

### CORS
Backend ya permite:
```python
allow_origins = ["http://localhost:8082", "http://localhost:8081", "http://localhost:8083"]
```

---

## 📦 Docker Compose Actualizado

```yaml
# docker-compose.yml
services:
  db:
    # ... (sin cambios)
  
  redis:
    # ... (sin cambios)
  
  backend:
    # ... (sin cambios)
    # Puerto 8000
  
  admin:
    # ... (sin cambios)
    # Puerto 8082
  
  tenant:
    # ... (sin cambios)
    # Puerto 8081
  
  tpv:  # ✨ NUEVO
    build: ./apps/tpv
    ports:
      - "8083:80"
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1
      - VITE_TPV_MODE=kiosk
    volumes:
      - ./apps/tpv:/app
    depends_on:
      - backend
```

---

## ✅ Próximos Pasos

### 1. Crear Proyecto TPV (30 min)
```bash
# Desde la raíz
cd apps
npm create vite@latest tpv -- --template react-ts

cd tpv
npm install
npm install -D tailwindcss postcss autoprefixer
npm install idb workbox-window @tanstack/react-query

# Configurar Tailwind, PWA, etc.
```

### 2. Implementar Componentes (4-6 horas)
- ProductGrid.tsx
- Cart.tsx
- PaymentScreen.tsx
- Offline sync

### 3. Service Worker (2 horas)
- Cache productos
- Queue ventas offline
- Background sync

### 4. Docker + Nginx (1 hora)
- Dockerfile
- nginx.conf (puerto 80)
- docker-compose.yml (añadir servicio)

---

**¿Quieres que cree la app TPV completa ahora?**

Será:
- PWA independiente
- Conecta al mismo backend
- UI tipo kiosco
- Offline-first
- Touch-optimized

Tiempo estimado: 2-3 horas de implementación.
