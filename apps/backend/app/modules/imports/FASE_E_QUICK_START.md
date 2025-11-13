# Fase E - Quick Start Guide

## Instalación y primeros pasos

### 1. Verificar salud del sistema
```bash
python -m app.modules.imports.cli health
```

Debe mostrar:
```
🏥 Health Check:
  ✅ Parsers: X registrados
  ✅ IA Provider: local
  ✅ IA Threshold: 0.7
  ✅ IA Cache: True
  ✅ Database: Connected
✅ Sistema listo
```

### 2. Listar parsers disponibles
```bash
python -m app.modules.imports.cli list-parsers
```

Verá algo como:
```
📋 Parsers Disponibles:

  ID: csv_invoices
    Doc Type: invoices
    Extensiones: .csv
    Descripción: CSV invoices parser
```

### 3. Clasificar un archivo
```bash
python -m app.modules.imports.cli classify --path /ruta/archivo.csv
```

### 4. Validar batch (sin procesar)
```bash
python -m app.modules.imports.cli batch-import \
  --folder /ruta/carpeta \
  --validate \
  --dry-run
```

### 5. Procesar batch completo
```bash
python -m app.modules.imports.cli batch-import \
  --folder /ruta/carpeta \
  --doc-type invoice \
  --country EC \
  --validate \
  --promote \
  --report results.json
```

## Ejemplos por caso de uso

### Caso 1: Importar facturas CSV Ecuador
```bash
python -m app.modules.imports.cli batch-import \
  --folder /data/facturas \
  --doc-type invoice \
  --pattern "*.csv" \
  --country EC \
  --validate \
  --promote

# Ver reporte
cat batch_import_report.json | python -m json.tool
```

### Caso 2: Validar sin procesar (QA)
```bash
python -m app.modules.imports.cli batch-import \
  --folder /pending/facturas \
  --doc-type invoice \
  --validate \
  --no-promote \
  --dry-run \
  --report qa_validation.json

# Ver errores
python -c "import json; \
d=json.load(open('qa_validation.json')); \
[print(r) for r in d['results'] if r['status']=='validation_error']"
```

### Caso 3: Importar desde legacy (migración)
```bash
# 1. Simular
python -m app.modules.imports.cli batch-import \
  --folder /backup/legacy_invoices \
  --doc-type invoice \
  --validate \
  --dry-run \
  --report migration_test.json

# 2. Revisar reporte
python -c "import json; d=json.load(open('migration_test.json')); \
print(f\"Success: {d['summary']['successful']}, Failed: {d['summary']['failed']}\")"

# 3. Si está bien, procesar
python -m app.modules.imports.cli batch-import \
  --folder /backup/legacy_invoices \
  --doc-type invoice \
  --validate \
  --promote \
  --report migration_complete.json
```

### Caso 4: Cron diario
```bash
# Script: /scripts/import_daily.sh
#!/bin/bash
FOLDER="/var/imports/incoming"
REPORT="/var/imports/logs/$(date +%Y%m%d_%H%M%S).json"

python -m app.modules.imports.cli batch-import \
  --folder "$FOLDER" \
  --validate \
  --promote \
  --skip-errors \
  --report "$REPORT"

# Enviar notificación
if grep -q '"failed": 0' "$REPORT"; then
  echo "✓ Import exitoso" | mail -s "Daily Import OK" admin@company.com
else
  cat "$REPORT" | mail -s "⚠️ Import con errores" admin@company.com
fi
```

## Referencia rápida de opciones

```
--folder         Carpeta a importar (REQUERIDO)
--doc-type       invoice | expense | product | bank_tx (opcional, auto-detecta)
--pattern        *.csv, *.xlsx, 2025_*.csv (default: *.*)
--country        EC, ES, MX (para validación por país)
--validate       Validar documentos (default: true)
--promote        Guardar en BD (default: false)
--dry-run        Simular sin cambios (default: false)
--skip-errors    Continuar ante errores (default: true)
--report         Archivo JSON de salida (default: batch_import_report.json)
--recursive      Buscar en subcarpetas (default: true)
--parser         Forzar parser específico (optional)
```

## Interpretar reportes

### Resumen
```bash
jq '.summary' batch_import_report.json
```

### Archivos exitosos
```bash
jq '.results[] | select(.status=="success")' batch_import_report.json
```

### Errores de validación
```bash
jq '.results[] | select(.status=="validation_error") | {filename, errors}' batch_import_report.json
```

### Errores de parser
```bash
jq '.results[] | select(.status=="parser_error") | {filename, errors}' batch_import_report.json
```

### Estadísticas
```bash
jq '.summary | {total: .total_files, success: .successful, failed: .failed, time_sec: (.total_time_ms/1000)}' batch_import_report.json
```

## Troubleshooting

### "No parsers registered"
```bash
python -m app.modules.imports.cli list-parsers
# Si no aparecen, revisar app/modules/imports/parsers/__init__.py
```

### "No files found"
```bash
# Verificar patrón
ls /ruta/carpeta/*.csv
# Ajustar --pattern
```

### "Validation errors"
```bash
# Ver detalles
jq '.results[] | select(.status=="validation_error")' batch_import_report.json

# Validar con país
python -m app.modules.imports.cli batch-import \
  --folder /data \
  --country EC \
  --validate --dry-run
```

### "Database connection"
```bash
python -m app.modules.imports.cli health
# Verificar credenciales DB
```

## Próximos pasos

1. **Usar en desarrollo**:
   ```bash
   python -m app.modules.imports.cli batch-import \
     --folder tests/fixtures \
     --validate --dry-run
   ```

2. **Integrar con scheduler** (cron, APScheduler, etc.)

3. **Monitorear reportes**:
   ```bash
   watch -n 60 'ls -lh batch_import_report_*.json | tail -5'
   ```

4. **Actualizar BD periodicamente**:
   ```bash
   python -m app.modules.imports.cli batch-import \
     --folder /var/imports/pending \
     --validate --promote --skip-errors
   ```

## Links

- [FASE_E_BATCH_IMPORT.md](./FASE_E_BATCH_IMPORT.md) - Documentación completa
- [FASE_E_COMPLETADA.md](./FASE_E_COMPLETADA.md) - Resumen técnico
- [IMPORTADOR_PLAN.md](./IMPORTADOR_PLAN.md) - Plan general
- [PARSER_REGISTRY.md](./PARSER_REGISTRY.md) - Parsers disponibles
