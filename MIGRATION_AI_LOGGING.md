# 🔄 Migración - Tablas de Logging de IA

## 📋 Resumen

Agregar tablas para logging, análisis y recuperación de IA:
- `ai_request_logs` - Todos los requests/responses
- `ai_error_analysis` - Análisis de patrones de error
- `ai_error_recovery` - Intentos de recuperación

## 🚀 Opción 1: Alembic Migration (Recomendado)

### Paso 1: Crear la migración
```bash
cd apps/backend

# Generar archivo de migración
alembic revision --autogenerate -m "Add AI logging tables"
```

### Paso 2: Verificar el archivo generado
```bash
# Debería crear: alembic/versions/xxxx_add_ai_logging_tables.py
# Revisar que incluya las 3 tablas
```

### Paso 3: Aplicar migración
```bash
# Development
alembic upgrade head

# Production (con backup primero)
pg_dump -U postgres database_name > backup.sql
alembic upgrade head
```

### Paso 4: Verificar
```bash
# Conectar a BD y verificar tablas
psql -U postgres -d database_name -c "\dt ai_*"

# Deberías ver:
#  - public | ai_request_logs       | table
#  - public | ai_error_analysis     | table
#  - public | ai_error_recovery     | table
```

---

## 🛠️ Opción 2: SQL Directo

Si Alembic no funciona o prefieres SQL directo:

### Crear tablas
```sql
-- Tabla de logs
CREATE TABLE IF NOT EXISTS ai_request_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(50) UNIQUE NOT NULL,
    tenant_id VARCHAR(36),
    module VARCHAR(50),
    user_id VARCHAR(36),
    task VARCHAR(20) NOT NULL,
    prompt_length INTEGER NOT NULL,
    prompt_hash VARCHAR(64),
    temperature FLOAT DEFAULT 0.3,
    max_tokens INTEGER,
    model_requested VARCHAR(50),
    provider_used VARCHAR(20) NOT NULL,
    provider_model VARCHAR(50),
    status VARCHAR(20) DEFAULT 'success',
    response_content_length INTEGER DEFAULT 0,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0,
    fallback_used VARCHAR(20),
    confidence_score FLOAT,
    user_feedback VARCHAR(20),
    correction_applied VARCHAR(255),
    request_metadata JSONB,
    response_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para queries comunes
CREATE INDEX idx_ai_logs_status_created ON ai_request_logs(status, created_at);
CREATE INDEX idx_ai_logs_module_task ON ai_request_logs(module, task);
CREATE INDEX idx_ai_logs_tenant_created ON ai_request_logs(tenant_id, created_at);
CREATE INDEX idx_ai_logs_created_at ON ai_request_logs(created_at);
CREATE INDEX idx_ai_logs_provider ON ai_request_logs(provider_used);
CREATE INDEX idx_ai_logs_request_id ON ai_request_logs(request_id);

-- Tabla de análisis de errores
CREATE TABLE IF NOT EXISTS ai_error_analysis (
    id SERIAL PRIMARY KEY,
    error_pattern VARCHAR(100) UNIQUE,
    error_code VARCHAR(50),
    error_message_pattern VARCHAR(255) NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    last_occurred TIMESTAMP,
    probable_cause TEXT,
    suggested_action TEXT,
    resolution_status VARCHAR(50) DEFAULT 'open',
    auto_correction_enabled VARCHAR(50),
    correction_config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_ai_error_pattern ON ai_error_analysis(error_pattern);
CREATE INDEX idx_ai_error_last_occurred ON ai_error_analysis(last_occurred);

-- Tabla de recuperación
CREATE TABLE IF NOT EXISTS ai_error_recovery (
    id SERIAL PRIMARY KEY,
    request_log_id INTEGER,
    strategy_name VARCHAR(50) NOT NULL,
    step_number INTEGER,
    action_taken VARCHAR(100),
    was_successful VARCHAR(20),
    recovery_time_ms INTEGER,
    recovery_result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_recovery_request ON ai_error_recovery(request_log_id);
CREATE INDEX idx_ai_recovery_strategy ON ai_error_recovery(strategy_name);
```

### Ejecutar en psql
```bash
psql -U postgres -d your_database < ai_logging_tables.sql

# O si estás dentro de psql
\i ai_logging_tables.sql
```

---

## 📝 Opción 3: Genera SQL desde Modelos

Si quieres que SQLAlchemy genere SQL:

```python
# En Python terminal
from app.models.ai_log import AIRequestLog, AIErrorAnalysis, AIErrorRecovery
from app.config.database import engine

# Crear todas las tablas
AIRequestLog.__table__.create(engine, checkfirst=True)
AIErrorAnalysis.__table__.create(engine, checkfirst=True)
AIErrorRecovery.__table__.create(engine, checkfirst=True)

print("Tablas creadas!")
```

O desde script:
```bash
python3 << 'EOF'
from app.config.database import engine
from app.models.ai_log import AIRequestLog, AIErrorAnalysis, AIErrorRecovery, Base

# Crear todas las tablas definidas en models
Base.metadata.create_all(engine)
print("✅ Tablas creadas!")
EOF
```

---

## ✅ Verificación Post-Migración

### Verificar tablas
```bash
# Conectar a BD
psql -U postgres -d your_database

# Listar tablas
\dt ai_*

# Ver estructura de tabla
\d ai_request_logs

# Ver índices
\di ai_*
```

### Verificar con Python
```python
from sqlalchemy import inspect
from app.config.database import engine

inspector = inspect(engine)

# Listar tablas
tables = inspector.get_table_names()
print("Tablas:", tables)

# Verificar que existen
expected = ['ai_request_logs', 'ai_error_analysis', 'ai_error_recovery']
for table in expected:
    if table in tables:
        print(f"✅ {table} existe")
    else:
        print(f"❌ {table} falta")

# Ver columnas
columns = inspector.get_columns('ai_request_logs')
for col in columns:
    print(f"  - {col['name']} ({col['type']})")
```

---

## 🔄 Rollback (Si algo falla)

### Con Alembic
```bash
# Ver current version
alembic current

# Rollback a versión anterior
alembic downgrade -1

# O específico
alembic downgrade <revision>
```

### Manual SQL
```sql
-- Eliminar tablas (solo si es necesario)
DROP TABLE IF EXISTS ai_error_recovery CASCADE;
DROP TABLE IF EXISTS ai_error_analysis CASCADE;
DROP TABLE IF EXISTS ai_request_logs CASCADE;

-- Luego reintentar migración
```

---

## 📊 Estructura de Datos

### ai_request_logs
```
Columna                   | Tipo      | Descripción
--------------------------|-----------|----------------------------------
id                         | SERIAL    | PK
request_id                 | VARCHAR   | UUID único para tracking
tenant_id                  | VARCHAR   | ID del tenant
module                     | VARCHAR   | copilot, imports, incidents
user_id                    | VARCHAR   | ID del usuario que solicitó
task                       | VARCHAR   | classification, analysis, etc
prompt_length              | INTEGER   | Largo del prompt
prompt_hash                | VARCHAR   | SHA256 del prompt
temperature                | FLOAT     | Parámetro de temperatura
max_tokens                 | INTEGER   | Límite de tokens
model_requested            | VARCHAR   | Modelo solicitado
provider_used              | VARCHAR   | ollama, ovhcloud, openai
provider_model             | VARCHAR   | Modelo exacto usado
status                     | VARCHAR   | success, error, timeout, fallback
response_content_length    | INTEGER   | Tamaño de respuesta
tokens_used                | INTEGER   | Tokens consumidos
processing_time_ms         | INTEGER   | Tiempo de procesamiento
error_message              | TEXT      | Si hubo error
error_code                 | VARCHAR   | Código de error
retry_count                | INTEGER   | Cuántos reintentos
fallback_used              | VARCHAR   | Qué fallback se usó
confidence_score           | FLOAT     | Confianza de respuesta
user_feedback              | VARCHAR   | Feedback del usuario
correction_applied         | VARCHAR   | Si se corrigió
request_metadata           | JSONB     | Contexto personalizado
response_metadata          | JSONB     | Metadata del provider
created_at                 | TIMESTAMP | Cuándo se creó
updated_at                 | TIMESTAMP | Última actualización
```

### ai_error_analysis
```
Columna                    | Tipo      | Descripción
---------------------------|-----------|----------------------------------
id                          | SERIAL    | PK
error_pattern               | VARCHAR   | Patrón único (ollama_timeout)
error_code                  | VARCHAR   | Código de error
error_message_pattern       | VARCHAR   | Patrón del mensaje
occurrence_count            | INTEGER   | Cuántas veces ocurrió
last_occurred               | TIMESTAMP | Última ocurrencia
probable_cause              | TEXT      | Causa probable
suggested_action            | TEXT      | Acción sugerida
resolution_status           | VARCHAR   | open, resolved, wontfix
auto_correction_enabled     | VARCHAR   | Estrategia de corrección
correction_config           | JSONB     | Config de corrección
created_at                  | TIMESTAMP | Creación del análisis
updated_at                  | TIMESTAMP | Última actualización
resolved_at                 | TIMESTAMP | Cuándo se resolvió
```

### ai_error_recovery
```
Columna                    | Tipo      | Descripción
---------------------------|-----------|----------------------------------
id                          | SERIAL    | PK
request_log_id              | INTEGER   | FK a ai_request_logs
strategy_name               | VARCHAR   | retry, fallback, simplify
step_number                 | INTEGER   | Número de paso
action_taken                | VARCHAR   | Descripción de acción
was_successful              | VARCHAR   | true, false
recovery_time_ms            | INTEGER   | Cuánto tardó
recovery_result             | JSONB     | Resultado de acción
created_at                  | TIMESTAMP | Cuándo ocurrió
```

---

## 🧹 Mantenimiento

### Cleanup automático (script)
```python
# apps/backend/scripts/cleanup_ai_logs.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.models.ai_log import AIRequestLog

def cleanup_old_logs(days=7):
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    deleted = db.query(AIRequestLog).filter(
        AIRequestLog.created_at < cutoff
    ).delete()
    
    db.commit()
    db.close()
    
    print(f"Eliminated {deleted} logs older than {days} days")

if __name__ == "__main__":
    cleanup_old_logs(days=7)
```

Ejecutar periódicamente:
```bash
# Cron job (daily)
0 2 * * * cd /app && python scripts/cleanup_ai_logs.py

# O como tarea celery
celery beat
```

### Monitorear tamaño de tablas
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  AND tablename LIKE 'ai_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🔐 Backup antes de migración

```bash
# PostgreSQL backup completo
pg_dump -U postgres -d your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup específico de BD
pg_dump -U postgres --table='ai_*' -d your_database > ai_tables_backup.sql

# Restore si algo va mal
psql -U postgres -d your_database < backup_20250216_143022.sql
```

---

## 📞 Troubleshooting

### "Error: relation does not exist"
```
→ Tablas no fueron creadas
→ Ejecutar migración de nuevo
→ Verificar con \d ai_request_logs
```

### "Error: duplicate key value"
```
→ Índice único ya existe
→ Usar IF NOT EXISTS en crear tabla
→ O: DROP TABLE IF EXISTS ... CASCADE; antes de crear
```

### "Error: permission denied"
```
→ Usuario no tiene permisos
→ Conectar como superuser (postgres)
→ GRANT ALL ON TABLE ai_* TO your_user;
```

### "Migración muy lenta"
```
→ Si tabla existente es muy grande, índices pueden tardarse
→ Crear índices por separado:
   CREATE INDEX CONCURRENTLY idx_name ON table(column);
```

---

## ✅ Checklist

- [ ] Backup de BD
- [ ] Crear/ejecutar migración
- [ ] Verificar tablas existen
- [ ] Verificar índices
- [ ] Probar insert en tablas
- [ ] Importar routers en main.py
- [ ] Probar endpoints `/api/v1/ai/logs/*`
- [ ] Configurar cleanup periódico
- [ ] Documentar en README

---

**Implementado**: Sistema completo de logging en BD  
**Status**: ✅ Listo para migración
