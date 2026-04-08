# Importador Checklist

Ultima actualizacion: 2026-04-08

## Objetivo

Dejar el modulo importador con una sola entrada publica de subida, sin rastro del flujo legacy `upload`, y luego ejecutar las mejoras de velocidad y deshardcodeo sobre `run-async`.

## Estado actual

- Entrada publica vigente: `POST /api/v1/importador/run-async`
- Flujo legacy eliminado del codigo: `POST /api/v1/importador/upload`
- Ruta frontend vigente: `importar`
- Nota: siguen apareciendo trazas historicas de `/api/v1/importador/upload` en logs viejos. No es codigo activo.

## Resumen ejecutivo

- Hecho: eliminacion completa del flujo legacy `upload`
- Hecho: instrumentacion de tiempos por etapa en procesamiento y worker async
- Hecho: optimizacion OCR inicial
  OCR con variantes priorizadas, rescate mas barato y reutilizacion de `easyocr.Reader(...)`
- Hecho parcial: heuristicas OCR movidas a runtime config
  `ocr_config` ya controla DPI PDF, contrast/sharpness, idiomas OCR, `easyocr_gpu`, angulos, thresholds, trim/perspective y limites Excel; quedan detalles menores de integracion aun fijos en codigo
- Hecho parcial: routing y regex movidos a config
  aliases/labels de routing, categorias, normalizacion de filename, patrones fiscales y fallbacks base de routing ya salen de runtime seed/config
- Hecho parcial: prompts partidos logicamente y trazables
  el importador ya persiste `prompt_full` y `prompt_parts`, y varios fragmentos fallback del prompt ahora salen de `prompt_config`
- Hecho: optimizacion inicial de Ollama
  concurrencia configurable por `base_url` + `OLLAMA_MAX_CONCURRENCY`
- Hecho: corte de reruns AI redundantes
  ya no rerunea cuando la recipe nueva solo aporta `prompt_system`
- Hecho parcial: snapshots/recipes
  reuso exacto mejorado con `fingerprint_signature` y `fingerprint_kind`, backfill automatico en snapshots viejos tocados
- Hecho: indexacion DB inicial para snapshots
  migracion SQL aplicada para `fingerprint_hash`, `fingerprint_signature` y `fingerprint_kind`
- Hecho parcial: prefiltro SQL para fuzzy reuse Excel
  migracion SQL aplicada en DB dev local para `fingerprint_headers_flat` + indice GIN; el overlap final sigue en Python
- Pendiente principal: medir percentiles reales, reducir mas scans Python-side, y mover hardcoding restante a DB/config
- Hecho parcial: thresholds de `pre_classifier`
  ahora salen de runtime config / seed (`imp_config` modulo `pre_classifier`), con fallback defensivo en codigo solo si falla la carga

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

- [x] Medir duracion por etapa base en procesamiento: OCR, recipe resolution, config, pre-classifier, AI, fallback, rerun, routing, staging, update
- [x] Persistir tiempos por documento en `raw_ai_json.run`
- [x] Exponer tiempos en logs estructurados por `document_id`
- [x] Exponer tiempos de borde de task por documento en worker async
- [ ] Confirmar percentiles reales antes de optimizar

## Bloque 2: Cuellos de botella de velocidad

- [x] Revisar OCR multi-variante y limitar combinaciones por perfil de variante
- [x] Evitar recrear `easyocr.Reader(...)` por documento/pagina
- [x] Revisar serializacion de Ollama por semaforo global
- [x] Hacer configurable la concurrencia de Ollama por entorno (`OLLAMA_MAX_CONCURRENCY`)
- [x] Detectar y eliminar reruns AI redundantes cuando la recipe nueva solo aporta `prompt_system`
- [ ] Reducir mas scans Python-side de snapshots y recipes
  Hecho parcial: reuso exacto por `fingerprint_signature`, filtro por `fingerprint_kind` y prefiltro SQL por `fingerprint_headers_flat` para Excel

## Bloque 3: Cero hardcoding

- [x] Pasar thresholds de `pre_classifier` a DB/config
  Se resolvieron via runtime config + `runtime_seed.json`; queda un fallback defensivo en codigo si falla la carga de config
- [x] Pasar heuristicas OCR a DB/config
  Hecho para knobs operativos de OCR imagen/PDF/Excel via `ocr_config`; el hardcoding remanente ya no esta en thresholds/idioma sino en detalles menores de integracion
- [x] Pasar listas y patrones fijos de routing a DB/config
  `routing_field_aliases`, `routing_field_labels`, `doc_categories` y fallbacks base de routing ahora viven en runtime seed/config
- [x] Pasar regex fiscales y reglas de doc_type a DB/config
  normalizacion de filename y `tax_id_patterns` ya salen de config; `doc_type_patterns` ya estaban fuera de codigo
- [x] Pasar prompts fallback restantes a DB/config
  `prompt_config` ya gobierna fragmentos clave de armado: fallback vision system, structured classification preamble/preview, labels de respuesta/reglas/instrucciones y reglas extras de year sanity / line items
- [x] Guardar el prompt completo enviado a AI, no truncado
  ahora se persisten `prompt_full` y `prompt_parts`; `prompt_sent` queda truncado solo por compatibilidad
- [ ] Auditar defaults que hoy nacen en codigo y decidir si quedan en seed o en DB

## Bloque 4: Recipes y snapshots

- [x] Documentar contract exacto de `content_json`
- [ ] Indexar mejor fingerprint exacto y fuzzy reuse
  Hecho parcial: snapshots nuevos guardan `fingerprint_signature`, `fingerprint_kind` y `fingerprint_headers_flat`; migraciones DB aplicadas en dev, falta medir efecto real
- [ ] Reducir comparaciones Python-side en snapshots recientes
  Hecho parcial: fallback acotado, mejor reutilizacion exacta y prefiltro SQL para Excel; el fuzzy reuse sigue comparando overlap en Python
- [ ] Definir politica clara de reuso vs recreacion vs reproceso por learning version

## Contrato `content_json`

`content_json` vive en `icu_recipe_snapshot.content_json` y es el snapshot congelado que usa el importador para reuso, prompts, learning y matching.

### Claves base esperadas en snapshots nuevos

- `fingerprint_hash`: hash SHA-256 del fingerprint normalizado
- `fingerprint`: fingerprint estructural del documento
- `fingerprint_signature`: serializacion JSON estable del fingerprint normalizado para reuso exacto
- `fingerprint_kind`: tipo del fingerprint
  valores actuales: `excel`, `text`
- `fingerprint_headers_flat`: lista normalizada y ordenada de headers Excel para prefiltro SQL en fuzzy reuse
  solo aplica a snapshots `excel`
- `prompt_system`: prompt system congelado para ese snapshot
- `prompt_user`: prompt user congelado para ese snapshot o `null`
- `model`: modelo congelado para ese snapshot o `null`

### Shape de `fingerprint`

- Si `fingerprint_kind = "excel"`:
  `{"kind":"excel","sheets":{"<sheet>":{"headers":[...],"column_types":{"<col>":"<type>"}}}}`
- Si `fingerprint_kind = "text"`:
  `{"kind":"text","campos":[...],"formato":"PDF|IMAGE_OCR|XML|TXT|..."}`  
  `tipo_doc` no forma parte del fingerprint de texto actual

### Claves opcionales de recipes auto-generadas

- `sheet_profiles`: perfiles completos de hojas para snapshots Excel/CSV
- `fuzzy_source_snapshot_id`: snapshot origen usado para heredar prompts en fuzzy reuse Excel

### Claves opcionales de learning/cache

- `learned_analysis`: cache de clasificacion reutilizable por fingerprint
  shape actual:
  `{"structured":{"doc_type","confidence","reasoning","updated_at"},"default":{"doc_type","confidence","reasoning","updated_at"}}`
- `learning_version`: entero monotono; sube cuando cambia aprendizaje reutilizable
- `learning_updated_at`: timestamp ISO UTC del ultimo cambio de learning
- `field_descriptions`: hints base persistidos para campos
- `learned_field_descriptions`: hints aprendidos desde confirmaciones de usuario
- `field_learning_memory`: memoria agregada por campo
  shape actual por campo:
  `{"confirmed_count","corrected_count","confirmed_examples":[],"corrected_examples":[],"last_original_value","last_confirmed_value"}`
- `learning_prompt_user`: bloque de prompt derivado de confirmaciones previas

### Claves legacy o toleradas

- `model_config.model`: algunos snapshots viejos pueden no tener `model` plano y resolver el modelo desde `model_config.model`
- `fingerprint_signature` y `fingerprint_kind`: pueden faltar en snapshots viejos
  el código hace backfill cuando los reutiliza
- `fingerprint_headers_flat`: puede faltar en snapshots viejos y se backfillea para Excel cuando el snapshot se reutiliza o por migracion SQL
- `fingerprint_hash`: si falta, el código intenta recuperarse por `fingerprint_signature` o por comparación del fingerprint

### Productores actuales

- `resolve_auto_recipe(...)`: crea snapshots Excel/CSV
- `resolve_auto_recipe_from_text(...)`: crea snapshots PDF/XML/imagen/TXT
- `remember_snapshot_learning(...)`: actualiza `learned_analysis`, `learning_version`, `learning_updated_at`
- `apply_learning_to_snapshot(...)`: actualiza `learned_field_descriptions`, `field_learning_memory`, `learning_prompt_user`, `learning_version`, `learning_updated_at`
- `_ensure_snapshot_fingerprint_metadata(...)`: backfill de `fingerprint_signature`, `fingerprint_kind`, `fingerprint_headers_flat` y, si falta, `fingerprint_hash`

### Consumidores actuales

- `find_snapshot_by_hash(...)`: reuso exacto por `fingerprint_hash`, luego `fingerprint_signature`, luego fallback por fingerprint
- `find_similar_excel_snapshot(...)`: fuzzy reuse Excel por overlap de headers
- `_snapshot_recipe_config(...)`: resuelve `prompt_system`, `prompt_user`, `model`, `field_descriptions`
- `get_snapshot_learning(...)`: lee `learned_analysis`
- `get_snapshot_learning_version(...)`: lee `learning_version`
- `should_reprocess_existing_document(...)`: compara `learning_version` actual vs version aplicada al documento
- `build_snapshot_review_hints(...)`: usa `field_learning_memory`

### Invariantes reales hoy

- Todo snapshot nuevo debe tener al menos fingerprint + prompts + modelo aunque `prompt_user` y `model` vengan en `null`
- `learning_version` puede no existir en snapshots sin aprendizaje
- `learned_analysis` no contiene extraction completa, solo clasificacion reutilizable
- `field_descriptions` final efectivo = merge de `field_descriptions` base + `learned_field_descriptions`
- El contrato todavia no esta versionado formalmente dentro de `content_json`

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

## Smoke real con `C:\\gestiqcloud\\importacion`

- [x] OCR real sobre PDF con texto embebido
  `factura_proveedor_stock_alto_insumos.pdf` -> `format=PDF`, `pages=3`, `elapsed_ms~881`, `text_len=4521`
- [x] OCR real sobre imagen
  `WhatsApp Image 2026-03-24 at 16.29.16.jpeg` -> `format=IMAGE_OCR`, `pages=1`, `elapsed_ms~7655`, `text_len=169`
- [ ] Repetir smoke real sobre PDF escaneado puro
- [ ] Repetir smoke real sobre Excel grande y CSV

## Riesgos abiertos

- [ ] Confirmar que ninguna integracion externa siga llamando al endpoint viejo
- [ ] Confirmar que el cambio de ruta frontend `upload` -> `importar` no rompe bookmarks internos
- [ ] Ejecutar tests en entorno con `fastapi` y demas dependencias; en este entorno no fue posible
- [ ] Ejecutar pruebas con dependencias completas (`fastapi`, `sqlalchemy`, `httpx`, `numpy`) para validar OCR, provider AI y tests de importador
  En `.venv` ya se pudieron correr tests focalizados; el bloqueo actual es la politica global de coverage del repo, no el codigo tocado
- [x] Verificar plan de consulta real tras aplicar `2026-04-08_001_icu_snapshot_fingerprint_indexes`
  En DB dev actual (`icu_recipe_snapshot` con 1 fila) Postgres sigue prefiriendo `Seq Scan`; se confirmo que la query correcta debe incluir el predicado parcial `content_json ? '<clave>'` y que asi queda index-eligible
- [x] Aplicar migracion `2026-04-08_002_icu_snapshot_excel_header_index` en DB dev local
  La DB dev actual no tenia snapshots Excel; se valido el camino con una fila temporal y rollback. En cardinalidad minima el planner uso el indice por `fingerprint_kind` y dejo `fingerprint_headers_flat` como filtro

## Notas de trabajo

- Si aparece otro residuo de `upload`, se borra o se renombra en esta misma lista antes de seguir con mejoras.
- No meter optimizaciones de velocidad sin instrumentacion minima; si no, se vuelve opinion y no evidencia.
- OCR ahora prioriza un subconjunto configurable de variantes para Tesseract, deja el resto como rescate con menos PSMs y reutiliza `easyocr.Reader(...)`.
- `ocr_config` ya gobierna DPI PDF, contraste, nitidez, idiomas OCR, `easyocr_gpu`, angulos de deskew, thresholds binarios, parametros de trim/perspective y limites del parser Excel.
- Routing ya consume `routing_field_aliases`, `routing_field_labels`, `doc_categories`, `routing_fallback_profiles` y `routing_fallback_rules` desde config/seed en lugar de constantes de modulo.
- `pre_classifier` ya consume `filename_normalization` y `tax_id_patterns` desde config/seed; la extraccion fiscal dejo de depender de regex inline.
- Partir prompts si merece la pena, pero por gobernanza y debugging, no por latencia: el path de texto sigue enviando un solo `full_prompt` a `AIService.query`; para una separacion real a nivel transporte habria que extender el stack AI para soportar `messages` tambien fuera del vision path.
- Los thresholds de `pre_classifier` ya no nacen en el modulo como defaults operativos: se cargan desde runtime config / seed del modulo `pre_classifier`; el fallback en codigo queda solo como red de seguridad si la carga falla.
- La concurrencia de Ollama ya no queda fijada al importar el modulo; se resuelve por `base_url` y `OLLAMA_MAX_CONCURRENCY`.
- El rerun AI ya no se ejecuta si la recipe candidata solo cambia `prompt_system`; ahora exige hints utiles (`field_descriptions`, `prompt_user`, `model` o senales aprendidas).
- Los snapshots nuevos guardan `fingerprint_signature` y `fingerprint_kind` para acelerar reuso exacto y reducir scans de fallback; los snapshots viejos siguen con fallback acotado.
- Existe migracion SQL aplicada para backfill seguro de `fingerprint_kind` e indices por `fingerprint_hash`, `fingerprint_signature` y `fingerprint_kind`; falta validar el plan real de consulta y el impacto en produccion.
- El plan real fue verificado en la DB dev local: con 1 fila, el planner usa `Seq Scan` por costo. La forma correcta de query ya fue ajustada para respetar el predicado del indice parcial y permitir `Index Scan` cuando la cardinalidad lo justifique.
- El prefiltro SQL de Excel fue validado con un snapshot temporal y rollback. Con cardinalidad minima, Postgres eligio el indice por `fingerprint_kind`; el filtro por `fingerprint_headers_flat` queda listo para ganar valor cuando el volumen de snapshots Excel crezca.
