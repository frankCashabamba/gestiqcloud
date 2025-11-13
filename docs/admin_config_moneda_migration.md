# Admin Config – Moneda Migration

Este documento explica cómo está construido el nuevo stack de “Monedas” en `admin_config`, para que el resto del equipo pueda migrar los demás catálogos (idiomas, países, etc.) siguiendo el mismo patrón.

## Estructura general

```
app/
└── modules/
    └── admin_config/
        ├── application/
        │   └── monedas/
        │       ├── dto.py
        │       ├── ports.py
        │       └── use_cases.py
        ├── infrastructure/
        │   └── monedas/
        │       └── repository.py
        └── interface/http/
            └── admin.py  (endpoints actualizados)
```

### DTOs (`application/monedas/dto.py`)
- `MonedaIn`: datos de entrada (`code`, `name`, `symbol`, `active`).
- `MonedaOut`: respuesta enviada al frontend (`id`, `code`, `name`, `symbol`, `active`).

### Puerto (`application/monedas/ports.py`)
- `MonedaRepo`: protocolo que define las operaciones soportadas (`list`, `get`, `create`, `update`, `delete`).

### Casos de uso (`application/monedas/use_cases.py`)
- `ListarMonedas`
- `ObtenerMoneda`
- `CrearMoneda`
- `ActualizarMoneda`
- `EliminarMoneda`
Todos heredan de `BaseUseCase` y dependen únicamente del puerto.

### Repositorio (`infrastructure/monedas/repository.py`)
- Implementa `MonedaRepo` usando SQLAlchemy y el modelo `Moneda` (tabla `currencies`).
- Expone métodos CRUD y convierte los modelos ORM a `MonedaOut`.

### Router (`interface/http/admin.py`)
- Los endpoints `/config/moneda` ahora crean instancias del repositorio + use cases.
- Helpers locales convierten los `MonedaRead` de Pydantic a/desde `MonedaIn`.
- Se dejó un `try/except ValueError` para responder 404 cuando el use case lanza `moneda_no_encontrada`.

## Cómo migrar otro catálogo

1. **Crear DTOs** en `application/<catalogo>/dto.py`.
2. **Definir puerto** `Protocol` con las operaciones necesarias (`ports.py`).
3. **Crear casos de uso** (`use_cases.py`) derivando de `BaseUseCase` y usando el puerto.
4. **Implementar repositorio** SQLAlchemy en `infrastructure/<catalogo>/repository.py`.
5. **Actualizar el router**:
   - Importar los nuevos use cases/repos en `interface/http/admin.py`.
   - Reemplazar llamadas a `*_crud` por los use cases.
   - Manejar los errores de “no encontrado” convirtiendo `ValueError` en HTTP 404.
6. **Eliminar referencias al CRUD legacy** (`app/modules/admin_config/crud.py`) para ese catálogo.
7. Repetir el proceso para el siguiente catálogo.

## Catálogos pendientes de migrar

- Idiomas (`core_idioma`)
- Países (`countries`)
- Días de semana (`core_dia`)
- Horarios de atención (`core_horarioatencion`)
- SectorPlantilla (`core_sectorplantilla`)
- Tipos de empresa (`core_tipoempresa`)
- Tipos de negocio (`core_tiponegocio`)
- Timezones (`timezones`)
- Locales (`locales`)

> Tip: Puedes clonar las carpetas `application/monedas` e `infrastructure/monedas`, renombrarlas y ajustar únicamente el modelo/DTO para cada catálogo.
