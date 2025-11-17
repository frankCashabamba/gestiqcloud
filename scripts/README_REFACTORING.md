# 🔄 Guía de Refactoring: Español → Inglés

Automatización para cambiar nombres de campos, tablas y variables de español a inglés en todo el proyecto.

## 📋 Pasos

### 1️⃣ Configurar Cambios

Edita `CAMPO_CHANGES_CONFIG.py` con tus cambios específicos:

```python
FIELD_MAPPINGS = {
    "nombre": "name",
    "descripcion": "description",
    "creado_en": "created_at",
    "actualizado_en": "updated_at",
    "activo": "active",
}

DATABASE_MIGRATIONS = {
    "empresas": {
        "nombre": "name",
        "descripcion": "description",
    },
    "usuarios": {
        "nombre": "name",
        "correo": "email",
    },
}
```

### 2️⃣ Hacer Backup

```bash
git commit -m "Backup antes de refactoring español->inglés"
git tag backup-spanish-fields
```

### 3️⃣ Aplicar Cambios de Código

Ejecuta el script de renombramiento masivo:

```bash
python scripts/mass_rename_fields.py
```

Este script:
- ✅ Procesa todos los archivos (.py, .ts, .tsx, .js, .jsx, .json)
- ✅ Respeta límites de palabra (no cambia "nombreComplet" si buscas "nombre")
- ✅ Preserva camelCase/snake_case
- ✅ Muestra reporte de cambios

### 4️⃣ Generar Migraciones Alembic

```bash
python scripts/generate_alembic_migration.py
```

Este script:
- ✅ Crea archivos de migración Alembic
- ✅ Genera las operaciones `upgrade()` y `downgrade()`
- ✅ Guarda en `alembic/versions/`

Luego aplica las migraciones:
```bash
python ops/scripts/migrate_all_migrations.py --database-url "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
```

### 5️⃣ Generar Tipos TypeScript (Opcional)

```bash
python scripts/generate_ts_types.py
```

Este script:
- ✅ Extrae modelos Python
- ✅ Genera interfaces TypeScript
- ✅ Mantiene tipos sincronizados

### 6️⃣ Pruebas

```bash
# Backend
cd apps/backend
pytest

# Frontend (si aplica)
cd apps/frontend
npm test
```

## 🔍 Verificación Manual

Después de ejecutar los scripts, revisa:

1. **imports.py** - Asegúrate que `__all__` tiene los nombres correctos
2. **routers/** - Que los endpoints mapeen correctamente
3. **schemas/** - Que los Pydantic models usen los campos nuevos
4. **frontend/** - Que las llamadas API usen los nuevos campos

## ⚠️ Cuidado

- Los scripts usan regex, así que pueden tener falsos positivos
- Siempre haz un commit antes
- Revisa el diff antes de hacer push
- Algunos campos pueden tener lógica especial (enums, validadores)

## 🔙 Revertir

```bash
git reset --hard HEAD
git checkout backup-spanish-fields
```

## 📊 Checklist

- [ ] Configuré CAMPO_CHANGES_CONFIG.py
- [ ] Hice backup con git tag
- [ ] Ejecuté mass_rename_fields.py
- [ ] Generé migraciones Alembic
- [ ] Ejecuté alembic upgrade head
- [ ] Los tests pasan
- [ ] Revisé cambios con git diff
- [ ] Hice commit con los cambios

## 🆘 Solución de Problemas

### Error: "wc command not found"
Asegúrate de ejecutar desde PowerShell en Windows

### Cambios no aplicados
- Verifica que FIELD_MAPPINGS no está vacío
- Revisa los EXCLUDE_DIRS
- Busca archivos con encoding especial

### Migraciones fallan
- Verifica que la tabla existe
- Revisa que no hay conflictos con otras migraciones
- Ejecuta `alembic downgrade` si necesitas revertir
