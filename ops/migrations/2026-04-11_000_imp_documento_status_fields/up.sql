-- Migration: imp_documento_status_fields
-- Separa las dimensiones de estado del documento importado:
--   - extraction_status : qué pasó con la extracción (ok / partial / failed)
--   - reprocess_status  : disponibilidad del archivo original para reproceso
--
-- Problema que resuelve: cuando el payload de Celery ya no existe al intentar
-- reprocesar, el sistema marcaba el documento como FAILED aunque tuviera datos
-- extraídos válidos de un ciclo anterior. Con estos campos el fallo de reproceso
-- se registra en reprocess_status sin contaminar el estado del workflow (estado).

ALTER TABLE imp_documento
    ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(20) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS reprocess_status  VARCHAR(20) DEFAULT NULL;

-- extraction_status : 'ok' | 'partial' | 'failed'
-- reprocess_status  : 'available' | 'unavailable' | 'failed'

COMMENT ON COLUMN imp_documento.extraction_status IS
    'Resultado de la extracción: ok=datos extraídos correctamente, partial=extracción incompleta, failed=no se pudo extraer nada';

COMMENT ON COLUMN imp_documento.reprocess_status IS
    'Disponibilidad del archivo original: available=puede reprocesarse, unavailable=payload expirado/eliminado, failed=último intento de reproceso falló';

-- Backfill conservador: documentos ya en REVIEW/CONFIRMED con datos = extracción ok.
-- Documentos en FAILED sin datos = extracción fallida.
-- El resto se deja NULL (legado sin info suficiente).
UPDATE imp_documento
   SET extraction_status = 'ok'
 WHERE estado IN ('REVIEW', 'CONFIRMED')
   AND datos_extraidos IS NOT NULL
   AND datos_extraidos::text != '{}';

UPDATE imp_documento
   SET extraction_status = 'failed'
 WHERE estado = 'FAILED'
   AND (datos_extraidos IS NULL OR datos_extraidos::text = '{}');

-- Index para queries de admin/monitoring por extraction_status
CREATE INDEX IF NOT EXISTS idx_imp_documento_extraction_status
    ON imp_documento (tenant_id, extraction_status)
    WHERE extraction_status IS NOT NULL;
