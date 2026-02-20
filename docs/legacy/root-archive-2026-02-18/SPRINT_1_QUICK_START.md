# SPRINT 1 - Quick Start Guide

## ⚡ Start Aquí

```bash
# 1. Ir a directorio de tenant
cd apps/tenant

# 2. Instalar dependencias (si no están)
npm install

# 3. Iniciar desarrollo
npm run dev

# 4. Ir a POS en navegador
# http://localhost:5173/pos  (o el puerto que uses)
```

---

## 🧪 Test Quick (5 minutos)

### Test 1: Toasts Funcionan
```
1. Abrir POS
2. Agregar 1 producto al carrito
3. Presionar F8 (Suspender venta)
   ✓ Debe aparecer toast verde: "Venta suspendida T######"
   ✓ Con botón "Deshacer"
4. Hacer clic en "Deshacer"
   ✓ Toast desaparece, carrito se restaura
```

### Test 2: Atajos de Teclado
```
1. Abrir POS
2. Presionar F2
   ✓ Input de búsqueda recibe foco (borde azul)
3. Presionar F4
   ✓ Se abre modal de cliente
4. Presionar Esc
   ✓ Modal se cierra
5. Presionar F9 (sin carrito)
   ✓ No abre pago (carrito vacío)
6. Agregar un producto
7. Presionar F9
   ✓ Se abre modal de pago (CurrentReceiptId necesario)
```

### Test 3: Responsive (Móvil)
```
1. Abrir DevTools (F12)
2. Toggle Device Toolbar (Ctrl+Shift+M)
3. Seleccionar iPhone SE (375px)
4. Observar:
   ✓ POSLayout aún no integrado (ver SPRINT 2)
   ✓ Pero useMediaQuery funciona en background
```

---

## 🐛 Troubleshooting

### Error: "useToast must be used within ToastProvider"
```
✓ Verificar que ToastProvider esté en main.tsx
✓ Ya debe estar en el código actual
```

### Atajos No Funcionan
```
✓ Verificar que useKeyboardShortcuts esté en POSView
✓ Ver console (F12 → Console)
✓ Presionar atajo y mirar si hay errores
```

### Toast No Aparece
```
✓ Verificar posición (esquina inferior derecha)
✓ Si no ve nada, abrir console y ejecutar:
   useToast().success("Test")
✓ El toast debe aparecer
```

### Búsqueda No Enfoca con F2
```
✓ searchInputRef debe estar en <input>
✓ Verificar que handleSearchElement esté correctamente referenciado
```

---

## 📁 Archivos Creados (Referencia Rápida)

```
HOOKS:
- apps/tenant/src/modules/pos/hooks/useKeyboardShortcuts.ts
- apps/tenant/src/modules/pos/hooks/useSinglePaymentFlow.ts
- apps/tenant/src/modules/pos/hooks/index.ts
- apps/tenant/src/hooks/useMediaQuery.ts

COMPONENTES:
- apps/tenant/src/modules/pos/components/POSTopBar.tsx
- apps/tenant/src/modules/pos/components/POSPaymentBar.tsx
- apps/tenant/src/modules/pos/components/POSLayout.tsx
- apps/tenant/src/modules/pos/components/POSKeyboardHelp.tsx

SISTEMA:
- apps/tenant/src/shared/toast.tsx (MODIFICADO)
- apps/tenant/src/modules/pos/POSView.tsx (MODIFICADO)

DOCUMENTOS:
- SPRINT_1_IMPLEMENTATION_SUMMARY.md
- SPRINT_1_CHECKLIST.md
- SPRINT_2_ACTION_PLAN.md
- POS_PRO_IMPLEMENTATION_SUMMARY.md
- SPRINT_1_QUICK_START.md (este archivo)
```

---

## 🎯 Checklist de Validación

```
ATAJOS:
☐ F2 enfoca búsqueda
☐ F4 abre cliente
☐ F6 pide descuento
☐ F8 suspende (toast + undo)
☐ F9 abre pago
☐ Esc cierra modales
☐ ↑↓ navegan listas (si aplica)

TOASTS:
☐ Suspender → toast.success()
☐ Error stock → toast.warning()
☐ Precio inválido → toast.error()
☐ Límite excedido → toast.warning()
☐ Toast desaparece automáticamente
☐ Toast con acción "Deshacer" funciona

RESPONSIVE (base):
☐ useMediaQuery funciona
☐ POSLayout component existe
☐ (Aún no integrado en POSView, será SPRINT 2)

GENERAL:
☐ POSView compila sin errores
☐ No hay console errors
☐ Toasts se muestran correctamente
☐ Atajos no interfieren con escribir
```

---

## 🔍 Debugging Tips

### Ver si Toast System está funcionando
```tsx
// Abrir console del navegador (F12)
// Pegar esto:
const ctx = React.useContext(ToastContext)
ctx.success("Test message")
// Debe aparecer toast
```

### Ver si Atajos están registrados
```tsx
// En POSView.tsx, agregar log:
useKeyboardShortcuts({
  onF2: () => {
    console.log('F2 pressed!')  // ← Agregar esto
    searchInputRef.current?.focus()
  },
  // ...
})
// Presionar F2, debe verse log en console
```

### Verificar estructura de componentes
```bash
# Desde apps/tenant:
find src/modules/pos/components -name "*.tsx" | sort
find src/modules/pos/hooks -name "*.ts" | sort
```

---

## 🚀 Próximos Pasos Después de Validar SPRINT 1

```
1. ✅ SPRINT 1 validado
2. 📋 Leer SPRINT_2_ACTION_PLAN.md
3. 🔨 Crear componentes CatalogSection.tsx y CartSection.tsx
4. 🔌 Integrar POSLayout en POSView render
5. 🎨 Crear modales (Descuento, Reanudar)
6. 💳 Unificar PaymentModal
7. 🧪 Testing full flow
```

---

## 💬 Resumen Rápido

**SPRINT 1**: Sistema de atajos + toasts profesionales ✅
- F2-F9 atajos funcionales
- Toast notifications con acciones
- Sistema undo en suspensiones
- Base para responsive (POSLayout lista)

**SPRINT 2**: Layout responsivo + pago unificado 📋
- Integrar POSLayout
- UNA pantalla de pago con tabs
- Modales en vez de prompts
- Búsqueda siempre enfocada

**SPRINT 3**: Refinamientos y roles avanzados 📋
- Rol Cajero (rápido)
- Rol Encargado (acceso total)
- Devoluciones mejoradas
- Confirmaciones elegantes

---

## 📞 Línea de Ayuda

Si algo no funciona:

1. **Revisar console** (F12 → Console)
   - Buscar errores rojos
   
2. **Revisar estructura**
   - ¿Todos los archivos están en su lugar?
   - ¿Imports correctos en POSView?

3. **Verificar ToastProvider**
   - ¿Está en main.tsx?
   - ¿POSView está dentro de ToastProvider?

4. **Test simple**
   - Abrir POS
   - Suspender venta (F8)
   - Ver si aparece toast

5. **Si aún no funciona**
   - Revisar SPRINT_1_CHECKLIST.md
   - Ver sección de Troubleshooting

---

**Good Luck! 🎉**

Ahora tienes un POS profesional con atajos, toasts y (próximamente) layout responsivo.

**Next**: Lee `SPRINT_2_ACTION_PLAN.md` para el siguiente nivel.
