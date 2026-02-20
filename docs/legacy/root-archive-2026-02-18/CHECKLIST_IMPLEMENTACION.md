# Checklist de Implementación - Permisos Frontend

## Pre-implementación ✅ COMPLETADO

- [x] Revisar sistema de permisos existente (backend)
- [x] Diseñar extensión sin modificar backend
- [x] Crear plan detallado (EXTENSION_PERMISOS_PLAN.md)
- [x] Implementar PermissionsContext
- [x] Implementar hooks (usePermission, usePermissionLabel)
- [x] Implementar componentes (ProtectedRoute, ProtectedButton, PermissionDenied)
- [x] Agregar i18n (permisos.json ES/EN)
- [x] Crear tests básicos
- [x] Integrar en AuthContext
- [x] Documentación (guías + ejemplos)

**Estado:** ✅ 100% - Listo para integración en módulos

---

## Fase 2: Integración Módulos (En Progreso)

### Subtarea: Billing Module

#### 2.1 Preparación
- [ ] Leer `EJEMPLO_INTEGRACION_BILLING.md`
- [ ] Revisar estructura actual de Billing
  ```bash
  ls apps/tenant/src/modules/billing/
  ```
- [ ] Hacer backup de archivos principales
  ```bash
  git checkout -b feature/billing-permissions
  ```

#### 2.2 Actualizar manifest.ts
- [ ] Verificar permisos en manifest
- [ ] Confirmar que coinciden con backend (`billing:read`, `billing:create`, etc.)
- [ ] Documentar permisos requeridos

**Comando:**
```bash
cat apps/tenant/src/modules/billing/manifest.ts | grep permissions
```

#### 2.3 Actualizar Routes.tsx
- [ ] Envolver rutas con `<ProtectedRoute permission="billing:read">`
- [ ] Proteger rutas de creación con `billing:create`
- [ ] Proteger rutas de edición con `billing:update`
- [ ] Agregar fallback `<PermissionDenied />`

**Template:**
```typescript
import ProtectedRoute from '@/auth/ProtectedRoute'
import PermissionDenied from '@/components/PermissionDenied'

<ProtectedRoute
  permission="billing:read"
  fallback={<PermissionDenied permission="billing:read" />}
>
  {/* Contenido protegido */}
</ProtectedRoute>
```

#### 2.4 Actualizar BillingList.tsx
- [ ] Importar `usePermission` y `ProtectedButton`
- [ ] Agregar check `can('billing:create')` antes de renderizar botón crear
- [ ] Reemplazar botones de acción con `<ProtectedButton>`
- [ ] Agregar lógica para deshabilitar acciones sin permiso

**Checklist por botón:**
- [ ] "Crear factura" → `<ProtectedButton permission="billing:create">`
- [ ] "Editar" → `<ProtectedButton permission="billing:update">`
- [ ] "Enviar" → `<ProtectedButton permission="billing:send">`
- [ ] "Pagar" → `<ProtectedButton permission="billing:pay">`
- [ ] "Eliminar" → `<ProtectedButton permission="billing:delete">`

#### 2.5 Actualizar BillingForm.tsx
- [ ] Agregar `usePermission()` al inicio
- [ ] Validar permiso requerido (create vs update)
- [ ] Si no tiene permiso → render `<PermissionDenied />`
- [ ] Botón guardar: `<ProtectedButton permission={requiredPerm}>`

#### 2.6 Actualizar BillingDetail.tsx
- [ ] Agregar acciones condicionadas por permisos
- [ ] Botón editar: `can('billing:update')`
- [ ] Botón enviar: `can('billing:send')`
- [ ] Botón pagar: `can('billing:pay')`
- [ ] Botón eliminar: `can('billing:delete')`

#### 2.7 Actualizar Services/API
- [ ] Revisar que API calls no cambien (backend sigue igual)
- [ ] Agregar tipo `Invoice` con permisos (opcional)
- [ ] Tests de servicios (sin cambios esperados)

#### 2.8 Tests Unitarios
- [ ] Test: BillingList sin permiso → sin botón crear
- [ ] Test: BillingList con permiso → botón crear visible
- [ ] Test: BillingForm sin permiso → PermissionDenied
- [ ] Test: usePermission con permisos parciales

**Comando para correr tests:**
```bash
npm run test -- modules/billing
```

#### 2.9 Tests E2E
- [ ] Login sin permisos → `/billing` redirige
- [ ] Login con `billing:read` → ve lista
- [ ] Sin `billing:create` → botón deshabilitado
- [ ] Con `billing:create` → puede crear
- [ ] Sin `billing:delete` → botón no visible
- [ ] Admin → todos los botones

**Crear:** `e2e/billing-permissions.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test('user without billing:read cannot access', async ({ page }) => {
  await loginAs(page, 'user_no_permisos')
  await page.goto('/billing')
  await expect(page.locator('text=No autorizado')).toBeVisible()
})

test('user with billing:create can create invoice', async ({ page }) => {
  await loginAs(page, 'user_billing_admin')
  await page.goto('/billing')
  await page.click('button:has-text("Nueva Factura")')
  await expect(page.locator('h1:has-text("Crear Factura")')).toBeVisible()
})
```

**Comando:**
```bash
npx playwright test e2e/billing-permissions.spec.ts
```

#### 2.10 Code Review
- [ ] Peer review del código
- [ ] Verificar que no haya cambios innecesarios en backend
- [ ] Tests pasan (unit + E2E)
- [ ] Sin warnings de linting

**Comando:**
```bash
npm run lint -- modules/billing
npm run test -- modules/billing
```

#### 2.11 Documentación Interna
- [ ] Agregar comentarios en code (`// Si no tiene permiso...`)
- [ ] Documentar flujos en README de módulo
- [ ] Actualizar TESTING.md si existe

#### 2.12 Documentación de Usuario
- [ ] Crear/actualizar guía para usuarios finales
- [ ] Listar todos los permisos requeridos
- [ ] Instrucciones: "Si no ves botón X, contacta admin"

**Template:**
```markdown
## Facturación - Permisos Requeridos

| Acción | Permiso | Descripción |
|--------|---------|-------------|
| Ver facturas | `billing:read` | Lista y detalles |
| Crear | `billing:create` | Nuevo formulario |
| Editar | `billing:update` | Modificar existentes |
| Enviar | `billing:send` | Enviar a cliente |
| Pagar | `billing:pay` | Registrar pagos |
| Eliminar | `billing:delete` | Remover facturas |
```

#### 2.13 Merge & Deploy
- [ ] Code review aprobado
- [ ] Todos los tests pasan
- [ ] Merge a `main` o rama release
- [ ] Deploy a staging
- [ ] Testing manual en staging
- [ ] Deploy a producción

**Comandos:**
```bash
git add .
git commit -m "feat: add permission controls to billing module

- Protect billing routes with ProtectedRoute
- Add permission checks in BillingList/Form/Detail
- Replace action buttons with ProtectedButton
- Add E2E tests for permission scenarios
- Document required permissions for users"

git push origin feature/billing-permissions

# Después de merge:
npm run build
# Deploy según tu proceso
```

---

### Subtarea: Einvoicing Module

Repetir pasos 2.1-2.13 para Einvoicing:

- [ ] 2.1 Preparación
- [ ] 2.2 Actualizar manifest.ts
- [ ] 2.3 Actualizar Routes.tsx
  - [ ] Proteger `/einvoicing` con `einvoicing:read`
  - [ ] Proteger envío con `einvoicing:send`
  - [ ] Proteger descarga con `einvoicing:download`
- [ ] 2.4 Actualizar componentes principales
- [ ] 2.5 Tests unitarios
- [ ] 2.6 Tests E2E
- [ ] 2.7 Code review
- [ ] 2.8 Documentación
- [ ] 2.9 Merge & Deploy

**Permisos esperados:**
```
einvoicing:read
einvoicing:send
einvoicing:download
einvoicing:retry
```

---

### Subtarea: Reconciliation Module

- [ ] 2.1 Preparación
- [ ] 2.2 Actualizar manifest.ts
- [ ] 2.3 Actualizar Routes.tsx
  - [ ] Proteger `/reconciliation` con `reconciliation:read`
  - [ ] Proteger coincidencias con `reconciliation:match`
  - [ ] Proteger resolución de disputas con `reconciliation:resolve`
- [ ] 2.4 Actualizar componentes
- [ ] 2.5 Tests
- [ ] 2.6 Code review
- [ ] 2.7 Documentación
- [ ] 2.8 Merge & Deploy

**Permisos esperados:**
```
reconciliation:read
reconciliation:match
reconciliation:resolve
```

---

## Fase 3: Resto de Módulos

Para cada módulo (Sales, Purchases, Inventory, Customers, Suppliers, HR, etc.):

- [ ] Crear rama feature: `feature/{modulo}-permissions`
- [ ] Seguir steps 2.1-2.13
- [ ] Estimar 2-4 horas por módulo
- [ ] Consolidar en una PR grande si son muchos

**Prioridad:**
1. Sales (crítico para ventas)
2. Purchases (crítico para compras)
3. Inventory (importante para stock)
4. Resto

---

## Fase 4: Validación Final

- [ ] Todos los módulos tienen ProtectedRoute
- [ ] Todos los botones usan ProtectedButton
- [ ] i18n cubre todos los permisos usados
- [ ] Tests E2E cubren escenarios principales
- [ ] Documentación actualizada
- [ ] No hay hardcodes de permisos
- [ ] Backend sin cambios (zero-impact)

---

## Testing Strategy

### Unit Tests (Por módulo)
```bash
npm run test -- modules/{modulo} --coverage
```

Cobertura mínima: 70%

### E2E Tests
```bash
npx playwright test e2e/{modulo}-permissions.spec.ts
```

Escenarios:
1. Usuario sin permisos → acceso denegado
2. Usuario con algunos permisos → algunos botones
3. Admin → acceso total
4. Cambio de permisos → refetch y UI actualiza

### Manual Testing (Staging)
1. Crear 3 usuarios con permisos diferentes
2. Login con cada uno
3. Verificar que botones aparecen/desaparecen correctamente
4. Verificar que backend devuelve 403 si intenta burlar permisos

---

## Métricas de Éxito

- [ ] **Coverage:** ≥70% en tests
- [ ] **Performance:** Sin regresión en load time
- [ ] **Compatibility:** 100% compatible con backend
- [ ] **Documentation:** Guías actualizadas
- [ ] **Adoption:** Todos los módulos integrados en 4 semanas

---

## Rollback Plan

Si hay problemas:

1. Revertir rama feature:
   ```bash
   git revert -m 1 {merge-commit}
   ```

2. PermissionsContext seguirá funcionando (no rompe nada)

3. Componentes sin `<ProtectedRoute>` siguen funcionando

4. Backend sin cambios → siempre funciona

---

## Timeline Estimado

| Fase | Módulos | Horas | Duración |
|------|---------|-------|----------|
| Pre-impl | Setup | 40 | ✅ Completado |
| Billing | 1 | 4 | 1 día |
| Einvoicing | 1 | 4 | 1 día |
| Reconciliation | 1 | 4 | 1 día |
| Otros | 10+ | 40 | 2 semanas |
| Documentación | Todas | 8 | 1 día |
| **Total** | **13+** | **100** | **~4 semanas** |

---

## Notas Importantes

1. **NO modificar backend** - Solo frontend
2. **Tests obligatorios** - Unitarios + E2E
3. **Documentación** - Para usuarios y desarrolladores
4. **Code review** - Antes de merge
5. **Staging primero** - Testing manual antes de prod
6. **Rollback rápido** - Si hay problemas

---

## Contactos/Escalación

- **Preguntas permisos:** Ver `GUIA_USO_PERMISOS.md`
- **Problemas técnicos:** Revisar `EXTENSION_PERMISOS_PLAN.md`
- **Integración:** Copiar `EJEMPLO_INTEGRACION_BILLING.md`
- **Documentación:** Actualizar según módulo

---

## Próximos Pasos Inmediatos

1. ✅ **HECHO:** Pre-implementación completada
2. → **AHORA:** Comenzar Integración Billing (hoy)
3. → **Mañana:** Tests E2E Billing
4. → **Próximos días:** Einvoicing + Reconciliation

**Comando para comenzar:**
```bash
git checkout -b feature/billing-permissions
# Empezar con step 2.3: Actualizar Routes.tsx
```

---

**Última actualización:** 2026-02-11
**Estado general:** En progreso (Pre-impl 100%, Fase 2 ready to start)
