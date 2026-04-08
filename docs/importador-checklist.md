# Importador Checklist

Ultima actualizacion: 2026-04-08

## Objetivo

Dejar el modulo importador con una sola entrada publica de subida, sin rastro del flujo legacy `upload`, y luego ejecutar las mejoras de velocidad y deshardcodeo sobre `run-async`.

## Estado actual

- Entrada publica vigente: `POST /api/v1/importador/run-async`
- Flujo legacy eliminado del codigo: `POST /api/v1/importador/upload`
- Ruta frontend vigente: `importar`
- Nota: siguen apareciendo trazas historicas de `/api/v1/importador/upload` en logs viejos. No es codigo activo.

## Checklist de limpieza

- [x] Eliminar endpoint backend `/importador/upload`
- [x] Eliminar flujo sync `upload_files(...)`
- [x] Eliminar `UploadResponse`
- [x] Dejar `process_import_document(...)` solo con modos `run` y `async`
- [x] Cambiar la ruta frontend de `upload` a `importar`
- [x] Renombrar pantalla de entrada a `ImportPage`
- [x] Renombrar componente de carga a `ImportIntake`
- [x] Cambiar session key de `importador.uploader.session.v1` a `importador.import.session.v1`
- [x] Mover tests del flujo viejo al flujo async real
- [x] Verificar que no quedan referencias de codigo a `/importador/upload`
- [ ] Ejecutar test suite del importador en entorno con dependencias completas
- [ ] Validar manualmente UI: dashboard -> importar -> documents -> reimportar

## Bloque 1: Instrumentacion de tiempos

- [ ] Medir duracion por etapa: enqueue, OCR, pre-classifier, AI, fallback, DB, routing, snapshot learning
- [ ] Persistir tiempos por documento en `raw_ai_json.run` o estructura equivalente
- [ ] Exponer tiempos en logs estructurados por `document_id` y `batch_id`
- [ ] Confirmar percentiles reales antes de optimizar

## Bloque 2: Cuellos de botella de velocidad

- [ ] Revisar OCR multi-variante y limitar combinaciones por tipo de archivo
- [ ] Evitar recrear `easyocr.Reader(...)` por documento/pagina
- [ ] Revisar serializacion de Ollama por semaforo global
- [ ] Hacer configurable la concurrencia de Ollama por tenant o entorno
- [ ] Detectar y eliminar reruns AI redundantes
- [ ] Revisar scans Python-side de snapshots y recipes

## Bloque 3: Cero hardcoding

- [ ] Pasar thresholds de `pre_classifier` a DB/config
- [ ] Pasar heuristicas OCR a DB/config
- [ ] Pasar listas y patrones fijos de routing a DB/config
- [ ] Pasar regex fiscales y reglas de doc_type a DB/config
- [ ] Pasar prompts fallback restantes a DB/config
- [ ] Guardar el prompt completo enviado a AI, no truncado
- [ ] Auditar defaults que hoy nacen en codigo y decidir si quedan en seed o en DB

## Bloque 4: Recipes y snapshots

- [ ] Documentar contract exacto de `content_json`
- [ ] Indexar mejor fingerprint exacto y fuzzy reuse
- [ ] Reducir comparaciones Python-side en snapshots recientes
- [ ] Definir politica clara de reuso vs recreacion vs reproceso por learning version

## Bloque 5: Validacion funcional

- [ ] Subida simple PDF
- [ ] Subida imagen OCR
- [ ] Subida Excel/CSV estructurado
- [ ] Reimportacion forzada desde detalle de documento
- [ ] Reuso de documento por hash
- [ ] Reproceso por learning version
- [ ] Encadenado predecessor/successor por mismo nombre y nuevo hash
- [ ] Batch con multiples archivos
- [ ] Batch con ZIP soportado en el flujo vigente

## Riesgos abiertos

- [ ] Confirmar que ninguna integracion externa siga llamando al endpoint viejo
- [ ] Confirmar que el cambio de ruta frontend `upload` -> `importar` no rompe bookmarks internos
- [ ] Ejecutar tests en entorno con `fastapi` y demas dependencias; en este entorno no fue posible

## Notas de trabajo

- Si aparece otro residuo de `upload`, se borra o se renombra en esta misma lista antes de seguir con mejoras.
- No meter optimizaciones de velocidad sin instrumentacion minima; si no, se vuelve opinion y no evidencia.
