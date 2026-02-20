# ⏳ TAREA 6 - Atajos de Teclado
## Instrucciones para Completar SPRINT 2 al 100%

**Duración:** 30 minutos
**Dificultad:** Baja
**Prioridad:** Alta

---

## 🎯 Objetivo

Integrar los atajos de teclado para abrir los modales:
- **F6** → Abre `DiscountModal`
- **F5** → Abre `ResumeTicketModal` (ya funciona, hay que mejorar)

---

## 🔧 Implementación

### Paso 1: Localizar useKeyboardShortcuts

**Archivo:** `apps/tenant/src/modules/pos/hooks/useKeyboardShortcuts.ts`

Lee el archivo para entender su estructura:

```bash
# En tu terminal:
cat apps/tenant/src/modules/pos/hooks/useKeyboardShortcuts.ts
```

### Paso 2: Buscar el binding F6

En el archivo `useKeyboardShortcuts.ts`, busca la línea que maneja F6:

```typescript
// Buscar algo como:
if (e.key === 'F6') {
  // Aquí hace algo
}
```

### Paso 3: Agregar binding para DiscountModal

Reemplaza lo que hace F6 actualmente con:

```typescript
if (e.key === 'F6') {
  onOpenDiscountModal()
  e.preventDefault()
  return
}
```

### Paso 4: Pasar el callback como prop

En `POSView.tsx`, cuando llamas a `useKeyboardShortcuts`, agrega:

```typescript
const { setupShortcuts } = useKeyboardShortcuts({
  // ... props existentes ...
  onOpenDiscountModal: () => setShowDiscountModal(true),
})
```

### Paso 5: Verificar F5

F5 debería abrir `ResumeTicketModal`. Si no funciona, agrega:

```typescript
if (e.key === 'F5') {
  e.preventDefault()
  setShowResumeTicketModal(true)
  return
}
```

---

## 📝 Cambios Específicos

### En useKeyboardShortcuts.ts

**ANTES:**
```typescript
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'F6') {
      // Lógica antigua (si existe)
      setGlobalDiscountPct(parseFloat(prompt(...) || ...))
    }
  }
  // ...
}, [])
```

**DESPUÉS:**
```typescript
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'F6') {
      onOpenDiscountModal?.()
      e.preventDefault()
      return
    }
    // ... resto de atajos ...
  }
  // ...
}, [onOpenDiscountModal])
```

### En POSView.tsx

**Agregar donde se llama useKeyboardShortcuts:**

```typescript
useKeyboardShortcuts({
  // props existentes...
  onF5: () => setShowResumeTicketModal(true),
  onF6: () => setShowDiscountModal(true),
})
```

---

## 🔍 Opciones Recomendadas

### Opción A (Recomendada): Callbacks en Hook
- Más limpio
- Mejor separación de responsabilidades
- El hook solo maneja keyboard, POSView maneja state

### Opción B: Directamente en Hook
- Más rápido
- El hook conoce del estado de POSView
- Menos props a pasar

---

## 📍 Ejemplos de Ubicación

### useKeyboardShortcuts.ts
```typescript
export function useKeyboardShortcuts(options: {
  // ... props existentes ...
  onF5?: () => void
  onF6?: () => void
}) {
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'F5') {
        e.preventDefault()
        options.onF5?.()
        return
      }
      if (e.key === 'F6') {
        e.preventDefault()
        options.onF6?.()
        return
      }
      // ... resto ...
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [options])
}
```

### POSView.tsx (donde se usa)
```typescript
// En el main component body:
useKeyboardShortcuts({
  // ... props que ya existen ...
  onF5: () => setShowResumeTicketModal(true),
  onF6: () => setShowDiscountModal(true),
})
```

---

## ✅ Testing de Tarea 6

### Manual Test
1. Abrir POS
2. Presionar F5 → ResumeTicketModal se abre
3. Presionar F6 → DiscountModal se abre
4. Presionar ESC → Modal se cierra
5. Presionar F5 nuevamente → Se abre otra vez

### Unit Test
```typescript
describe('useKeyboardShortcuts - F5/F6', () => {
  it('should call onF5 when F5 pressed', () => {
    const onF5 = jest.fn()
    const { rerender } = renderHook(() =>
      useKeyboardShortcuts({ onF5 })
    )

    fireEvent.keyDown(window, { key: 'F5' })
    expect(onF5).toHaveBeenCalled()
  })

  it('should call onF6 when F6 pressed', () => {
    const onF6 = jest.fn()
    renderHook(() => useKeyboardShortcuts({ onF6 }))

    fireEvent.keyDown(window, { key: 'F6' })
    expect(onF6).toHaveBeenCalled()
  })

  it('should prevent default F5 behavior', () => {
    const onF5 = jest.fn()
    renderHook(() => useKeyboardShortcuts({ onF5 }))

    const event = new KeyboardEvent('keydown', { key: 'F5' })
    const preventDefaultSpy = jest.spyOn(event, 'preventDefault')

    window.dispatchEvent(event)
    expect(preventDefaultSpy).toHaveBeenCalled()
  })
})
```

---

## 🔗 Verificación de Integración

### Checklist
- [ ] useKeyboardShortcuts.ts actualizado con F5/F6
- [ ] POSView.tsx pasa callbacks al hook
- [ ] Estados showDiscountModal y showResumeTicketModal existen
- [ ] Modales se abren al presionar F5/F6
- [ ] Modales se cierran con ESC
- [ ] No hay console errors
- [ ] F5/F6 no afectan otros atajos

---

## 🚨 Posibles Errores

### Error 1: "onF5 is not a function"
**Causa:** Callback no pasado correctamente
**Solución:** Verificar que POSView pase `onF5: () => ...` al hook

### Error 2: "F5 no abre modal"
**Causa:** Hook no reacciona a keydown
**Solución:** Verificar `useEffect` dependencies, agregar log en handler

### Error 3: "Modal no cierra"
**Causa:** ESC no funciona correctamente
**Solución:** Verificar que modal tenga `onKeyDown={handleKeyDown}`

---

## 📊 Estado Final

**Después de Tarea 6:**
- ✅ F5 → ResumeTicketModal
- ✅ F6 → DiscountModal
- ✅ SPRINT 2: 100% COMPLETADO
- ✅ Listo para testing QA
- ✅ Listo para code review

---

## 📝 Documentación Necesaria

Una vez completada Tarea 6, actualizar:
- [ ] SPRINT_2_PROGRESS.md (marcar Tarea 6 como completada)
- [ ] SPRINT_2_COMPLETADO.md (cambiar 83% a 100%)
- [ ] SPRINT_2_README.md (marcar Tarea 6 como ✅)

---

## 🎯 Criterio de Aceptación

✅ **PASS si:**
- F5 abre ResumeTicketModal
- F6 abre DiscountModal
- ESC cierra modales
- No hay console errors
- No afecta otros atajos

❌ **FAIL si:**
- F5 o F6 no abren modal
- Atajo no funciona desde primera vez
- Error en console
- Interfiere con otros atajos

---

## 🔗 Archivos Relacionados

- `apps/tenant/src/modules/pos/hooks/useKeyboardShortcuts.ts` ← **MODIFICAR**
- `apps/tenant/src/modules/pos/POSView.tsx` ← **MODIFICAR (integración)**
- `SPRINT_2_PROGRESS.md` ← **ACTUALIZAR**

---

## ⏱️ Estimado

| Paso | Tiempo |
|------|--------|
| Leer hook | 5 min |
| Implementar F5 | 5 min |
| Implementar F6 | 5 min |
| Testing manual | 5 min |
| Actualizar docs | 5 min |
| Buffer | 5 min |
| **TOTAL** | **30 min** |

---

## 💡 Tips

1. **Mantén consistencia** con el patrón existente en useKeyboardShortcuts
2. **Usa preventDefault()** en F5/F6 para evitar comportamiento del navegador
3. **Agrega logs** temporales para debugging
4. **Test en diferentes navegadores** si es posible
5. **Documenta cualquier cambio** en comments del código

---

## 🎉 Resultado Final

Una vez completada esta tarea:

```
SPRINT 2: 100% COMPLETADO ✅
├── ✅ Tarea 1: autoFocus búsqueda
├── ✅ Tarea 2: Layout responsivo (código listo)
├── ✅ Tarea 3: Componentes reutilizables
├── ✅ Tarea 4: Modales no bloqueantes
├── ✅ Tarea 5: Pago unificado
└── ✅ Tarea 6: Atajos de teclado
```

**Estado:** Listo para QA Testing y Code Review

---

**Instrucciones creadas:** Febrero 16, 2026
**Estimado:** 30 minutos
**Siguiente:** Testing + Code Review + Deployment
