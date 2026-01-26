# Aplicar Migraciones Sin Alembic

Como no usas alembic, aquí están las instrucciones para aplicar la migración SQL directamente.

## Opción 1: Script de Utilidad (Recomendado)

### 1. Hacer el script ejecutable

```bash
chmod +x ops/run_migration.sh
```

### 2. Ver migraciones disponibles

```bash
./ops/run_migration.sh status
```

### 3. Aplicar la migración

```bash
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
```

### 4. Deshacer si es necesario

```bash
./ops/run_migration.sh down 2026-01-22_001_add_pos_invoice_lines
```

## Opción 2: Ejecutar SQL Directamente con psql

### 1. Conectar a la base de datos

```bash
psql -U gestiqcloud_user -d gestiqcloud -h localhost
```

### 2. Ejecutar el archivo SQL

```bash
\i ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

### 3. Verificar que se creó la tabla

```sql
\dt pos_invoice_lines
```

Debería ver:
```
              List of relations
 Schema |         Name          | Type  | Owner
--------+-----------------------+-------+-------
 public | pos_invoice_lines     | table | postgres
```

### 4. Deshacer si es necesario

```bash
\i ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

## Opción 3: Desde Python (si tienes script propio)

Si tienes un script Python para manejar migraciones:

```python
import subprocess
import os

def run_migration(migration_name: str, direction: str = "up"):
    """Run migration using direct SQL execution"""
    migration_dir = f"ops/migrations/{migration_name}"
    sql_file = os.path.join(migration_dir, f"{direction}.sql")

    if not os.path.exists(sql_file):
        raise FileNotFoundError(f"Migration file not found: {sql_file}")

    # Run psql with the SQL file
    cmd = [
        "psql",
        "-h", "localhost",
        "-U", "gestiqcloud_user",
        "-d", "gestiqcloud",
        "-v", "ON_ERROR_STOP=1",
        "-f", sql_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False

    print(f"Migration '{migration_name}' applied successfully")
    return True

# Usar:
run_migration("2026-01-22_001_add_pos_invoice_lines", "up")
```

## Opción 4: Con Docker

Si usas Docker Compose:

```bash
# Ejecutar migración en el contenedor de base de datos
docker-compose exec -T postgres psql -U gestiqcloud_user -d gestiqcloud \
  < ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

## Verificación

Después de aplicar la migración, verifica:

```sql
-- Verificar tabla existe
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pos_invoice_lines');

-- Verificar índice existe
SELECT indexname FROM pg_indexes WHERE tablename = 'pos_invoice_lines';

-- Verificar estructura de la tabla
\d pos_invoice_lines
```

Deberías ver:

```
                    Table "public.pos_invoice_lines"
       Column        | Type | Collation | Nullable | Default
---------------------+------+-----------+----------+---------
 id                  | uuid |           | not null |
 pos_receipt_line_id | uuid |           |          |

Indexes:
    "pos_invoice_lines_pkey" PRIMARY KEY, btree (id)
    "idx_pos_invoice_lines_pos_receipt_line_id" btree (pos_receipt_line_id)

Foreign-key constraints:
    "pos_invoice_lines_id_fkey" FOREIGN KEY (id) REFERENCES invoice_lines(id) ON DELETE CASCADE
```

## Rollback (Deshacer)

Si necesitas deshacer la migración:

```bash
# Opción 1: Con script
./ops/run_migration.sh down 2026-01-22_001_add_pos_invoice_lines

# Opción 2: Con psql directo
psql -U gestiqcloud_user -d gestiqcloud \
  < ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

## Variables de Entorno

Puedes configurar las variables de conexión:

```bash
export DB_USER=gestiqcloud_user
export DB_NAME=gestiqcloud
export DB_HOST=localhost
export DB_PORT=5432

# Luego ejecutar
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
```

## Troubleshooting

### Error: "FATAL: Ident authentication failed"

Solución: Usar contraseña en el comando

```bash
PGPASSWORD=tu_password psql -U gestiqcloud_user -d gestiqcloud ...
```

O configurar `.pgpass`:

```bash
echo "localhost:5432:gestiqcloud:gestiqcloud_user:password" > ~/.pgpass
chmod 600 ~/.pgpass
```

### Error: "relation \"invoice_lines\" does not exist"

Solución: La tabla `invoice_lines` no existe. Ejecutar primero la migración consolidada:

```bash
./ops/run_migration.sh up 2025-11-21_000_complete_consolidated_schema
```

### Error: "already exists"

Solución: Es seguro ejecutar de nuevo. El script usa `IF NOT EXISTS`:

```bash
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
```

Se ejecutará sin errores la segunda vez.

## Seguimiento de Migraciones Aplicadas

Para mantener un registro de qué migraciones se han aplicado, puedes crear una tabla:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

Y registrar cada migración:

```sql
INSERT INTO schema_migrations (name) VALUES ('2026-01-22_001_add_pos_invoice_lines');
```

O hacerlo desde el script:

```bash
MIGRATION_NAME="2026-01-22_001_add_pos_invoice_lines"

# Aplicar migración
./ops/run_migration.sh up "$MIGRATION_NAME"

# Registrar en BD
psql -U gestiqcloud_user -d gestiqcloud -c \
  "INSERT INTO schema_migrations (name) VALUES ('$MIGRATION_NAME') ON CONFLICT (name) DO NOTHING;"
```

## Resumen Rápido

```bash
# 1. Ver qué migraciones hay
./ops/run_migration.sh status

# 2. Aplicar la nueva migración
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines

# 3. Verificar en psql
psql -U gestiqcloud_user -d gestiqcloud -c "\dt pos_invoice_lines"

# 4. Reiniciar backend
systemctl restart gestiqcloud-backend

# 5. Verificar en logs
tail -f /var/log/gestiqcloud/backend.log | grep -i "polymorphic\|pos"
```
