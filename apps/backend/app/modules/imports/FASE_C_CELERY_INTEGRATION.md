# Fase C - Integración con Celery
## Guía de Implementación de task_import_file()

**Fecha**: 2025-11-11
**Prioridad**: CRÍTICA
**Estimado**: 2-4 horas

---

## 🎯 Objetivo

Integrar la validación canónica (Fase C) en la tarea Celery `task_import_file()` para que:
1. Parsee documentos (Fase B)
2. Valide contra schema canónico (Fase C) ← NUEVO
3. Despache a handlers según tipo (Fase C) ← NUEVO
4. Guarde resultados en DB

---

## 📍 Ubicación Actual

Buscar `task_import_file()` en:
- `app/modules/imports/services.py`
- O `app/workers/celery_tasks.py`

---

## 🔄 Flujo Actual vs Nuevo

### Flujo Actual (Fase B)
```python
def task_import_file(batch_id, parser_id, file_key):
    # 1. Obtener batch y archivo
    batch = ImportBatch.get(batch_id)
    file_path = s3.download(file_key)
    
    # 2. Parsear
    parser = registry.get_parser(parser_id)
    result = parser['handler'](file_path)
    
    # 3. Guardar items
    for raw_item in result['items']:
        item = ImportItem(
            batch_id=batch_id,
            raw=raw_item,  # JSON tal cual del parser
            status='PENDING'
        )
        db.add(item)
    db.commit()
```

### Flujo Nuevo (Fase C)
```python
def task_import_file(batch_id, parser_id, file_key):
    # 1. Obtener batch y archivo
    batch = ImportBatch.get(batch_id)
    file_path = s3.download(file_key)
    
    # 2. Parsear
    parser = registry.get_parser(parser_id)
    result = parser['handler'](file_path)
    
    # 3. Validar y Promocionar (NUEVO - Fase C)
    for raw_item in result['items']:
        # Validar contra schema canónico
        is_valid, errors = validate_canonical(raw_item)
        
        promoted_id = None
        if is_valid:
            # Despachar a handler según doc_type
            handler_result = HandlersRouter.promote_canonical(
                db,
                batch.tenant_id,
                raw_item
            )
            promoted_id = handler_result.domain_id
            
            if not handler_result.skipped:
                item_status = 'OK'
            else:
                item_status = 'PROMOTED_PREVIOUSLY'
        else:
            item_status = 'ERROR_VALIDATION'
        
        # 4. Guardar resultado
        item = ImportItem(
            batch_id=batch_id,
            raw=raw_item,
            canonical_doc=raw_item,  # NUEVO: Schema canónico
            doc_type=raw_item.get('doc_type'),  # NUEVO
            status=item_status,  # NUEVO: OK|ERROR_VALIDATION|PROMOTED_PREVIOUSLY
            errors=errors if not is_valid else None,  # NUEVO
            promoted_to=HandlersRouter.get_target_for_type(
                raw_item.get('doc_type')
            ),  # NUEVO
            promoted_id=promoted_id,  # NUEVO
        )
        db.add(item)
    
    db.commit()
```

---

## 📝 Implementación Paso a Paso

### Paso 1: Importar Nuevas Funciones

```python
# En el archivo services.py (top)
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.domain.handlers_router import (
    HandlersRouter,
    handlers_router,
)
```

### Paso 2: Actualizar Firma de task_import_file()

```python
@shared_task(
    bind=True,
    name='imports.task_import_file',
    max_retries=3,
    default_retry_delay=60,
)
def task_import_file(
    self,
    import_batch_id: str,
    parser_id: str,
    file_key: str,
    tenant_id: str,  # NUEVO: para handlers
):
    """
    Importa archivo, valida y promociona a tablas destino.
    
    Flujo:
    1. Parsea documento (Fase B)
    2. Valida contra schema canónico (Fase C)
    3. Despacha a handler según doc_type (Fase C)
    4. Guarda resultados con lineage
    
    Args:
        import_batch_id: UUID del batch
        parser_id: ID del parser ('csv_products', 'xlsx_expenses', etc)
        file_key: Ruta S3 del archivo
        tenant_id: UUID del tenant
    """
```

### Paso 3: Implementar Lógica Principal

```python
def task_import_file(self, import_batch_id, parser_id, file_key, tenant_id):
    db = SessionLocal()
    s3_client = boto3.client('s3')
    
    try:
        # 1. Obtener batch
        batch = db.query(ImportBatch).filter(
            ImportBatch.id == import_batch_id
        ).first()
        
        if not batch:
            raise ValueError(f"Batch no encontrado: {import_batch_id}")
        
        # 2. Descargar archivo
        local_path = f"/tmp/{file_key.split('/')[-1]}"
        s3_client.download_file(
            Bucket=os.getenv('S3_BUCKET'),
            Key=file_key,
            Filename=local_path
        )
        
        # 3. Obtener parser
        parser = registry.get_parser(parser_id)
        if not parser:
            raise ValueError(f"Parser no encontrado: {parser_id}")
        
        # 4. Parsear archivo
        try:
            parse_result = parser['handler'](local_path)
            items = parse_result.get('items', [])
        except Exception as e:
            batch.status = 'ERROR_PARSING'
            db.add(batch)
            db.commit()
            raise
        
        # 5. NUEVO - Validar, Promocionar y Guardar
        created = 0
        skipped = 0
        failed = 0
        
        for idx, raw_item in enumerate(items):
            try:
                # 5a. Validar contra schema canónico
                is_valid, validation_errors = validate_canonical(raw_item)
                
                promoted_id = None
                promoted_to = None
                doc_type = raw_item.get('doc_type', 'other')
                
                if is_valid:
                    # 5b. Despachar a handler
                    try:
                        promote_result = HandlersRouter.promote_canonical(
                            db=db,
                            tenant_id=tenant_id,
                            canonical_doc=raw_item,
                        )
                        
                        if promote_result and not promote_result.skipped:
                            promoted_id = promote_result.domain_id
                            promoted_to = HandlersRouter.get_target_for_type(doc_type)
                            item_status = 'OK'
                            created += 1
                        elif promote_result and promote_result.skipped:
                            promoted_id = promote_result.domain_id
                            promoted_to = HandlersRouter.get_target_for_type(doc_type)
                            item_status = 'OK_SKIPPED'
                            skipped += 1
                        else:
                            item_status = 'ERROR_PROMOTION'
                            failed += 1
                    
                    except Exception as e:
                        logger.error(
                            f"Error promoting item {idx}: {str(e)}",
                            exc_info=True
                        )
                        item_status = 'ERROR_PROMOTION'
                        promoted_id = None
                        failed += 1
                else:
                    # 5c. Validación falló
                    item_status = 'ERROR_VALIDATION'
                    failed += 1
                
                # 5d. Guardar ImportItem
                import_item = ImportItem(
                    id=uuid4(),
                    batch_id=import_batch_id,
                    idx=idx,
                    raw=raw_item,
                    normalized=raw_item,  # En Fase C, canonical es normalized
                    canonical_doc=raw_item,  # NUEVO
                    doc_type=doc_type,  # NUEVO
                    status=item_status,
                    errors=(
                        [{"field": "general", "msg": msg} for msg in validation_errors]
                        if validation_errors
                        else []
                    ),
                    promoted_to=promoted_to,
                    promoted_id=promoted_id,
                    promoted_at=datetime.utcnow() if promoted_id else None,
                )
                db.add(import_item)
                
                # 5e. Guardar lineage si se promocionó
                if promoted_id and promoted_to:
                    lineage = ImportLineage(
                        id=uuid4(),
                        import_item_id=import_item.id,
                        promoted_to=promoted_to,
                        promoted_ref=promoted_id,
                        doc_type=doc_type,
                        created_at=datetime.utcnow(),
                    )
                    db.add(lineage)
            
            except Exception as e:
                logger.error(
                    f"Error processing item {idx}: {str(e)}",
                    exc_info=True
                )
                # Crear item con error
                import_item = ImportItem(
                    id=uuid4(),
                    batch_id=import_batch_id,
                    idx=idx,
                    raw=raw_item,
                    status='ERROR_PROCESSING',
                    errors=[{"field": "general", "msg": str(e)}],
                )
                db.add(import_item)
                failed += 1
        
        # 6. Actualizar batch
        batch.status = 'COMPLETED'
        batch.processed_count = len(items)
        batch.success_count = created
        batch.error_count = failed
        db.add(batch)
        
        # 7. Commit
        db.commit()
        
        logger.info(
            f"Import batch {import_batch_id}: "
            f"created={created}, skipped={skipped}, failed={failed}"
        )
        
        return {
            'batch_id': import_batch_id,
            'created': created,
            'skipped': skipped,
            'failed': failed,
            'total': len(items),
        }
    
    except Exception as e:
        logger.error(f"Fatal error in task_import_file: {str(e)}", exc_info=True)
        
        # Actualizar batch como fallido
        batch = db.query(ImportBatch).filter(
            ImportBatch.id == import_batch_id
        ).first()
        if batch:
            batch.status = 'ERROR'
            db.add(batch)
            db.commit()
        
        # Reintentar si no han agotado intentos
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            raise
    
    finally:
        db.close()
        # Limpiar archivo temporal
        if os.path.exists(local_path):
            os.remove(local_path)
```

---

## 🗄️ Cambios en Modelo ImportItem

**Agregar campos a `ImportItem` (ORM)**:

```python
class ImportItem(Base):
    # ... campos existentes ...
    
    # Fase C - Validación Canónica
    canonical_doc = Column(JSON)  # NUEVO: Doc validado
    doc_type = Column(String(50))  # NUEVO: invoice|expense|product|etc
    normalized = Column(JSON)  # Ya existe, pero ahora = canonical_doc
    
    # Fase C - Status mejorado
    status = Column(
        String(50),
        default='PENDING',
        # Valores: PENDING|OK|OK_SKIPPED|ERROR_VALIDATION|ERROR_PROMOTION|ERROR_PROCESSING
    )
    errors = Column(JSON, default=[])  # NUEVO: [{"field": "x", "msg": "y"}]
    
    # Fase C - Enrutamiento
    promoted_to = Column(String(50))  # NUEVO: invoices|expenses|products|etc
    promoted_id = Column(String(36))  # NUEVO: UUID del registro promovido
    promoted_at = Column(DateTime)  # NUEVO: Timestamp
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Agregar tabla ImportLineage (si no existe)**:

```python
class ImportLineage(Base):
    __tablename__ = "import_lineage"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    import_item_id = Column(UUID, ForeignKey("import_items.id"))
    promoted_to = Column(String(50))  # Tabla destino
    promoted_ref = Column(String(36))  # ID en tabla destino
    doc_type = Column(String(50))  # Tipo de documento
    created_at = Column(DateTime, default=datetime.utcnow)
    
    import_item = relationship("ImportItem", backref="lineage")
```

---

## 🧪 Prueba de Integración

### Test en Celery

```python
# tests/test_celery_import.py
import pytest
from celery import shared_task
from app.workers.imports import task_import_file


@pytest.mark.celery
def test_task_import_file_product_csv():
    """Test: CSV de productos → validate_canonical → promote → OK"""
    # Setup
    batch_id = "test-batch-1"
    parser_id = "csv_products"
    file_key = "uploads/test_products.csv"
    tenant_id = "tenant-123"
    
    # Mock
    # ... crear archivo de prueba ...
    
    # Execute
    result = task_import_file.apply_async(
        args=(batch_id, parser_id, file_key, tenant_id),
        task_id="test-task-1"
    )
    
    # Assert
    assert result.status == 'SUCCESS'
    assert result.result['created'] > 0
    
    # Verificar en DB
    batch = ImportBatch.get(batch_id)
    assert batch.status == 'COMPLETED'
    assert len(batch.items) > 0
    
    item = batch.items[0]
    assert item.doc_type == 'product'
    assert item.status in ['OK', 'OK_SKIPPED']
    assert item.promoted_to == 'products'


@pytest.mark.celery
def test_task_import_file_expense_xlsx():
    """Test: XLSX de gastos → validate_canonical → promote → OK"""
    # Similar al anterior pero para expenses
    pass


@pytest.mark.celery
def test_task_import_file_invalid_data():
    """Test: Datos inválidos → ERROR_VALIDATION"""
    # Crear archivo con datos malos
    # Verificar que items tienen status='ERROR_VALIDATION'
    # Verificar que errors está poblado
    pass
```

---

## 🔍 Debugging

### Verificar que funciona

```bash
# 1. Ejecutar test
pytest tests/test_celery_import.py -v -s

# 2. Verificar en DB
sqlite3 gestiq.db
SELECT id, doc_type, status, errors FROM import_items LIMIT 5;

# 3. Revisar logs
tail -f logs/celery.log | grep "Import batch"

# 4. Monitorear Celery
celery -A app.workers.celery_app events
```

---

## ⚠️ Consideraciones

1. **Transaccionalidad**: Usar `db.commit()` solo después de que todos los items se procesaron
2. **Errores de Promoción**: No deben causar fallo total del batch
3. **Reintentos**: Celery reintentará si hay error fatal
4. **Limpieza**: Eliminar archivo temporal incluso si hay error
5. **Logging**: Loguear todos los pasos para debugging

---

## ✅ Checklist de Implementación

- [ ] Importar `validate_canonical` y `HandlersRouter`
- [ ] Actualizar firma de `task_import_file()`
- [ ] Agregar lógica de validación
- [ ] Agregar lógica de promoción
- [ ] Crear ImportItem con nuevos campos
- [ ] Crear ImportLineage si no existe
- [ ] Agregar tests
- [ ] Ejecutar y verificar
- [ ] Documentar en README

---

## 📞 Troubleshooting

### "No module named 'app.modules.imports.domain.handlers_router'"
```
→ Verificar que handlers_router.py existe en domain/
→ Ejecutar: python -c "from app.modules.imports.domain.handlers_router import HandlersRouter"
```

### "AttributeError: 'PromoteResult' has no attribute 'domain_id'"
```
→ Verificar que PromoteResult tiene __init__ con domain_id
→ Revisar: app/modules/imports/domain/handlers.py línea 9
```

### ImportItem no tiene columna 'canonical_doc'
```
→ Ejecutar: alembic upgrade head
→ O crear migration:
   alembic revision --autogenerate -m "Add canonical_doc to ImportItem"
   alembic upgrade head
```

---

## 🚀 Siguiente Fase

Una vez integrado Celery:
1. Ejecutar suite de tests E2E
2. Validar con datos de producción (pequeña muestra)
3. Pasar a Fase D - IA Configurable

---

**Estimado de implementación**: 2-4 horas
**Complejidad**: MEDIA
**Impacto**: ALTO - Habilita todo el sistema de importación Fase C
