#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para traducir todos los strings hardcodeados en POSView.tsx"""
import re

# Leer el archivo
with open('apps/tenant/src/modules/pos/POSView.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazos seguros y exactos (sorted by line number para evitar conflictos)
changes = [
    # Línea 529: Stock insuficiente
    ("alert(`Stock insuficiente. Disponible: ${stock}`)",
     "alert(t('pos:errors.insufficientStock') + `: ${stock}`)"),
    
    # Línea 536-537: Stock bajo del mínimo
    ("alert(`Stock bajo del minimo de stock (${reorderPoint}). No se puede vender.`)",
     "alert(`${t('pos:errors.lowStockMinimum')} (${reorderPoint}).\n${t('pos:errors.noCanSell')}`)"),
    
    # Línea 731: Descuento línea
    ("const value = prompt('Descuento línea (%)',",
     "const value = prompt(t('pos:cart.lineDiscount') + ' (%)',"),
    
    # Línea 738: Notas de línea
    ("const value = prompt('Notas de línea', cart[index].notes || '')",
     "const value = prompt(t('pos:cart.lineNotes'), cart[index].notes || '')"),
    
    # Línea 773: Producto no encontrado (primera)
    ("const shouldCreate = confirm(`Producto no encontrado: ${code}\n¿Deseas crearlo?`)",
     "const shouldCreate = confirm(`${t('pos:errors.productNotFound')}: ${code}\n${t('pos:errors.confirmCreate')}`)"),
    
    # Línea 900: Producto no encontrado (segunda)
    ("const shouldCreate = confirm(`Producto no encontrado: ${code}\n¿Deseas crearlo?`)",
     "const shouldCreate = confirm(`${t('pos:errors.productNotFound')}: ${code}\n${t('pos:errors.confirmCreate')}`)"),
    
    # Línea 621: Invalid price (ya traducida en script anterior)
    
    # Línea 1191: No hay líneas en el carrito
    ("alert('No hay l?neas en el carrito')",
     "alert(t('pos:errors.emptyCart'))"),
    
    # Línea 956: Total supera límite
    ("alert('El total supera el limite para consumidor final. Se requieren datos.')",
     "alert(t('pos:errors.totalExceedsLimit'))"),
    
    # Línea 1173: Selecciona identificación
    ("alert('Selecciona el tipo de identificacion del comprador.')",
     "alert(t('pos:errors.selectIdentificationType'))"),
    
    # Línea 1177: Completa identificación
    ("alert('Completa nombre e identificacion del comprador.')",
     "alert(t('pos:errors.completeIdentification'))"),
    
    # Línea 1167: Requiere datos del comprador
    ("alert('El total requiere datos del comprador.')",
     "alert(t('pos:errors.requiresBuyerData'))"),
    
    # Línea 1322: No hay tickets en espera
    ("alert('No hay tickets en espera')",
     "alert(t('pos:errors.heldTickets'))"),
    
    # Línea 1331: ID no encontrado
    ("alert('ID no encontrado')",
     "alert(t('pos:errors.idNotFound'))"),
    
    # Línea 1345: No hay nada para reimprimir
    ("alert('No hay nada para reimprimir todavía.')",
     "alert(t('pos:errors.nothingToReprint'))"),
    
    # Línea 1361: No se pudo reimprimir
    ("alert('No se pudo reimprimir.')",
     "alert(t('pos:errors.reprintFailed'))"),
    
    # Línea 1402: Caja creada
    ("alert(`Caja creada: ${payload.name}`)",
     "alert(t('pos:register.createdSuccess') + `: ${payload.name}`)"),
    
    # Línea 1405: Error crear caja
    ("alert('No se pudo crear la caja. Revisa permisos o intenta desde Admin.')",
     "alert(t('pos:register.createdError'))"),
    
    # Línea 2041: Factura generada
    ("alert('Factura generada correctamente')",
     "alert(t('pos:errors.invoiceGeneratedSuccess'))"),
    
    # Línea 2214: Producto existente agregado (primera)
    ("alert('Producto existente agregado al carrito.')",
     "alert(t('pos:createProduct.existingAdded'))"),
    
    # Línea 2232: Producto existente agregado (segunda)
    ("alert('Producto existente agregado al carrito.')",
     "alert(t('pos:createProduct.existingAdded'))"),
    
    # Línea 2273: No se pudo crear producto
    ("alert('No se pudo crear el producto')",
     "alert(t('pos:createProduct.creationFailed'))"),
    
    # Línea 2323: Impresión finalizada
    ("alert('Impresion finalizada')",
     "alert(t('pos:errors.printingFinished'))"),
]

# Aplicar cada cambio
for old, new in changes:
    if old in content:
        content = content.replace(old, new)
        print(f'OK {old[:60]}')
    else:
        print(f'MISSING {old[:60]}')

# Escribir
with open('apps/tenant/src/modules/pos/POSView.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nDone!')
