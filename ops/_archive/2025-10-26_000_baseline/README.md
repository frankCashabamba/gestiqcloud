# Migración Baseline Consolidada - GestiQCloud

**Fecha**: 2025-10-26
**Versión**: 1.0.0

## Descripción

Migración consolidada que incluye todo el esquema necesario para el MVP:

- ✅ Multi-tenant con RLS (tenants UUID + core_empresa legacy)
- ✅ Autenticación (auth_user, tokens, audit)
- ✅ Usuarios y roles (usuarios_usuarioempresa)
- ✅ Productos y catálogo
- ✅ Inventario (warehouses, stock_items, stock_moves)
- ✅ POS completo (registers, shifts, receipts, payments)
- ✅ Facturación (invoices, invoice_lines)
- ✅ E-factura (SRI Ecuador + SII España)
- ✅ Store Credits y vales
- ✅ Numeración documental (doc_series)
- ✅ Webhooks y auditoría

## Orden de Ejecución

Esta es la ÚNICA migración necesaria para empezar desde cero.

## Rollback

El archivo `down.sql` elimina todas las tablas creadas.
