# Migración 2025-10-28_128: Crear Tablas Tipo Empresa y Tipo Negocio

## Propósito
Crea las tablas base `core_tipoempresa` y `core_tiponegocio` necesarias para el sistema de plantillas de sector.

## Cambios

### Nuevas Tablas
- `core_tipoempresa`: Tipos de empresa (Autónomo, PYME, Gran Empresa)
- `core_tiponegocio`: Sectores de negocio (Panadería, Taller, Retail, etc.)

### Datos Iniciales
- 3 tipos de empresa
- 8 tipos de negocio predefinidos

## Dependencias
- Ninguna (migración base)

## Siguiente
- 2025-10-28_129: Crear tabla core_sectorplantilla
