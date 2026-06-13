# Convención de rutas frontend

Fecha: 2026-06-13

## Decisión

Las rutas internas nuevas deben usar inglés canónico:

- `new`
- `edit`
- `orders`
- `recipes`
- `settings`

Los textos visibles se traducen por i18n. Las rutas legacy en español se mantienen como redirects cuando ya existen o cuando hay enlaces externos.

## Estado actual

Actualizado 2026-06-13:

- CRUD basico de `customers`, `expenses`, `billing`, `suppliers`, `users`, `purchases` y `quotes` usa `new/edit` como ruta canonica.
- Las rutas legacy `nuevo`, `nueva` y `:id/editar` quedan como redirects.
- Los links internos de esos modulos apuntan a `new/edit`.

Quedan rutas mixtas en:

- `accounting`: `plan-cuentas/nuevo`, `asientos/:id/editar`
- `hr`: aliases `vacaciones`, `nomina`, `fichajes`
- `productions`: `planificacion`, `ordenes`, `recetas`, `ingredientes`
- `finances`: `saldos`, `caja`, `bancos`
- `reports`: `ventas`, `inventario`, `financiero`, `resultado-real`, `margenes`
- `importador`: `importar`

## Regla de migración

1. Crear ruta inglesa canónica.
2. Mantener ruta española como `<Navigate replace />`.
3. Actualizar links internos a ruta inglesa.
4. No romper URLs existentes.
5. Documentar alias en README del módulo si el módulo es estable.

## Ejemplo

```tsx
<Route path="new" element={<Form />} />
<Route path="nuevo" element={<Navigate to="../new" replace />} />
```
