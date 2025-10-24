# 🏪 TPV GestiQCloud - Punto de Venta Universal

**Versión**: 1.0.0  
**Puerto**: 8083  
**Tipo**: PWA Offline-First

---

## 🎯 Características

- ✅ **Offline-First** - Funciona sin internet
- ✅ **Touch-Optimized** - Diseñado para tablets
- ✅ **Universal** - Cualquier industria (panadería, retail, etc.)
- ✅ **PWA Instalable** - Se instala como app nativa
- ✅ **Fullscreen** - Modo kiosko
- ✅ **Simple y Rápido** - UI minimalista para cajeros
- ✅ **Sync Automático** - Sincroniza ventas al reconectar

---

## 🚀 Inicio Rápido

### Desarrollo
```bash
cd apps/tpv

# Instalar
npm install

# Configurar
cp .env.example .env
# Editar .env con tu TENANT_ID

# Desarrollo
npm run dev

# Abrir
http://localhost:8083
```

### Producción
```bash
# Build
npm run build

# Docker
docker compose up -d tpv

# Acceder
http://localhost:8083
```

---

## 🎨 Diseño

### Pantalla Principal
- Grid de productos (2-6 columnas responsive)
- Carrito lateral con totales
- Búsqueda de productos
- Indicador online/offline

### Pantalla de Cobro
- Total grande y visible
- Botones método de pago grandes
- Calculadora de cambio (efectivo)
- Botones rápidos (+5€, +10€, +20€, +50€)

### Touch-Optimized
- Botones mínimo 56px (táctil)
- Sin scroll innecesario
- Feedback visual al tocar
- Vibración táctil (móviles)

---

## 🔌 Integración Backend

### Endpoints que Usa
```
GET  /api/v1/products          # Catálogo (cache)
GET  /api/v1/pos/shifts/current/{id}
POST /api/v1/pos/receipts      # Crear venta
POST /api/v1/pos/receipts/{id}/pay
GET  /api/v1/inventory/stock   # Stock disponible
```

### Headers Necesarios
```
X-Tenant-ID: <UUID>
Content-Type: application/json
```

### CORS
Backend debe permitir:
```
http://localhost:8083
```
(Ya configurado en docker-compose.yml)

---

## 📱 PWA Features

### Instalación
1. Chrome → Menú → "Instalar app"
2. Se instala como aplicación nativa
3. Funciona sin navegador

### Offline
- Cache de productos (24 horas)
- Queue de ventas pendientes
- Sync automático al reconectar
- Nunca pierde ventas

### Service Worker
- Cache-First para productos
- Network-First para ventas
- Background Sync para queue

---

## 🎓 Uso

### Vender
1. Click en producto → Añade al carrito
2. Ajustar qty con +/-
3. Click "COBRAR"
4. Seleccionar método (Efectivo/Tarjeta)
5. Si efectivo: ingresar monto recibido
6. Click "CONFIRMAR PAGO"
7. ✅ Venta completada

### Offline
1. Perder conexión → Indicador 🔴 Offline
2. Seguir vendiendo normalmente
3. Ventas se encolan localmente
4. Reconectar → Sync automático
5. ✅ Todas las ventas procesadas

---

## 🔧 Configuración

### Variables (.env)
```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_TENANT_ID=123e4567-e89b-12d3-a456-426614174000
VITE_TPV_MODE=kiosk
VITE_DEFAULT_TAX_RATE=0.21
```

### Personalización
- Logo: Editar header en `App.tsx`
- Colores: Modificar `tailwind.config.js`
- Emojis: Editar `ProductCard.tsx` función `getProductEmoji()`

---

## 📊 Estructura

```
apps/tpv/
├── src/
│   ├── components/
│   │   ├── ProductGrid.tsx      # Grid de productos
│   │   ├── ProductCard.tsx      # Card individual
│   │   ├── Cart.tsx             # Carrito lateral
│   │   ├── CartItem.tsx         # Item del carrito
│   │   ├── PaymentScreen.tsx   # Pantalla de cobro
│   │   └── OfflineIndicator.tsx # Estado conexión
│   ├── hooks/
│   │   ├── useProducts.ts       # Cache productos
│   │   ├── useCart.ts           # Estado carrito (Zustand)
│   │   └── useOffline.ts        # Estado online/offline
│   ├── services/
│   │   └── api.ts               # API calls
│   ├── db/
│   │   └── operations.ts        # IndexedDB
│   ├── App.tsx                  # App principal
│   ├── main.tsx
│   └── index.css
├── public/
│   ├── sw.js                    # Service Worker
│   └── manifest.json            # PWA manifest
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── Dockerfile
└── nginx.conf
```

---

## 🎯 Ventajas vs Tenant App

| Feature | Tenant App | TPV App |
|---------|------------|---------|
| Complejidad | Alta (15 módulos) | Mínima (solo vender) |
| Usuarios | Gerentes | Cajeros |
| UI | Desktop/forms | Kiosko/touch |
| Navegación | Router complejo | Sin router |
| Offline | Lite | Total |
| Velocidad | Normal | Ultra-rápida |
| Tablet | Sí | **Optimizado** |

---

## 🚀 Deploy

### Docker Compose
```bash
# Levantar todo (incluye TPV)
docker compose up -d

# Solo TPV
docker compose up -d tpv

# Logs
docker logs -f tpv
```

### Standalone
```bash
cd apps/tpv
npm run build
npx serve dist -p 8083
```

---

## ✅ Testing

### Local
```
http://localhost:8083
```

### En Tablet (misma red)
```
http://<IP-PC>:8083
Ejemplo: http://192.168.1.100:8083
```

### Offline
1. Abrir DevTools (F12)
2. Network → Offline
3. Seguir usando (debe funcionar)
4. Online → Sincroniza automático

---

## 🎉 Resultado

**TPV profesional, universal y offline-first** listo para producción.

- Funciona en cualquier tablet
- No pierde ventas nunca
- UI ultra-simple para cajeros
- Conecta al mismo backend que Admin y Tenant

**¡Listo para vender!** 🚀

---

**Versión**: 1.0.0  
**Build**: tpv-jan2025  
**Licencia**: Propietaria
