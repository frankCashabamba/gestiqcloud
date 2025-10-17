-- 102_einv_error_catalog.sql
-- Catálogo profesional de errores SRI/SII con i18n, patrones y overrides por tenant. Incluye función de explicación.

BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tipos
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'einv_severity') THEN
    CREATE TYPE einv_severity AS ENUM ('info','warning','error');
  END IF;
END $$;

-- Catálogo global (sin RLS). Permite especializar por plantilla (vertical) si se desea.
CREATE TABLE IF NOT EXISTS einv_error_catalog (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source einv_source NOT NULL,                -- 'SRI' | 'SII'
  code text,                                  -- código exacto (si aplica)
  pattern text,                               -- regex POSIX para hacer match en el detalle
  template_key text,                          -- opcional: especialización por vertical (ej: 'bazar','bakery')
  locale text NOT NULL DEFAULT 'es-ES',
  title text NOT NULL,
  message text NOT NULL,
  checklist jsonb NOT NULL DEFAULT '[]'::jsonb,
  severity einv_severity NOT NULL DEFAULT 'error',
  docs_url text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source, COALESCE(code,''), COALESCE(template_key,''), locale)
);

-- Overrides por tenant (con RLS) para textos o checklists propios
CREATE TABLE IF NOT EXISTS einv_error_overrides (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source einv_source NOT NULL,
  code text,
  pattern text,
  locale text NOT NULL DEFAULT 'es-ES',
  title text,
  message text,
  checklist jsonb,
  severity einv_severity,
  docs_url text,
  UNIQUE (tenant_id, source, COALESCE(code,''), locale)
);

ALTER TABLE einv_error_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE einv_error_overrides FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_tenant ON einv_error_overrides;
CREATE POLICY rls_tenant ON einv_error_overrides
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Función para resolver explicación (prioridad: override por tenant > catálogo por código > catálogo por patrón > fallback)
CREATE OR REPLACE FUNCTION explain_einv_error(
  p_source einv_source,
  p_code text,
  p_details text,
  p_locale text DEFAULT 'es-ES',
  p_template_key text DEFAULT NULL
) RETURNS jsonb AS $$
DECLARE
  r jsonb;
BEGIN
  -- 1) Override del tenant (exact code)
  SELECT jsonb_build_object(
    'title', COALESCE(title,'')::text,
    'message', COALESCE(message,'')::text,
    'checklist', COALESCE(checklist,'[]'::jsonb),
    'severity', COALESCE(severity,'error')::text,
    'docs_url', COALESCE(docs_url,'')::text,
    'source','override'
  ) INTO r
  FROM einv_error_overrides
  WHERE tenant_id = current_setting('app.tenant_id', true)::uuid
    AND source = p_source AND COALESCE(code,'') = COALESCE(p_code,'')
    AND locale = p_locale
  LIMIT 1;
  IF r IS NOT NULL THEN RETURN r; END IF;

  -- 2) Catálogo por código (con o sin template_key)
  SELECT jsonb_build_object(
    'title', title,
    'message', message,
    'checklist', checklist,
    'severity', severity::text,
    'docs_url', COALESCE(docs_url,'')::text,
    'source','catalog'
  ) INTO r
  FROM einv_error_catalog
  WHERE source = p_source
    AND COALESCE(code,'') = COALESCE(p_code,'')
    AND locale = p_locale
    AND (template_key IS NULL OR template_key = p_template_key)
  LIMIT 1;
  IF r IS NOT NULL THEN RETURN r; END IF;

  -- 3) Catálogo por patrón en detalles
  SELECT jsonb_build_object(
    'title', title,
    'message', message,
    'checklist', checklist,
    'severity', severity::text,
    'docs_url', COALESCE(docs_url,'')::text,
    'source','catalog-pattern'
  ) INTO r
  FROM einv_error_catalog
  WHERE source = p_source
    AND pattern IS NOT NULL
    AND locale = p_locale
    AND (template_key IS NULL OR template_key = p_template_key)
    AND (p_details ~ pattern)
  LIMIT 1;
  IF r IS NOT NULL THEN RETURN r; END IF;

  -- 4) Fallback simple
  RETURN jsonb_build_object(
    'title','No se encontró explicación específica',
    'message', COALESCE(p_details,'Error fiscal'),
    'checklist', jsonb_build_array('Revise NIF/RUC, totales, tipos de IVA/Impuesto','Reintente el envío'),
    'severity','error'
  );
END; $$ LANGUAGE plpgsql STABLE;

-- Seeds mínimos (puedes ampliar)
INSERT INTO einv_error_catalog(source, code, locale, title, message, checklist, severity)
VALUES
  ('SRI', NULL, 'es-EC', 'Clave de acceso inválida',
   'La clave de acceso del comprobante no es válida (formato o dígito verificador).',
   '["Verifique fecha de emisión y serie","Recalcule la clave de acceso","Vuelva a firmar y enviar"]', 'error'),
  ('SRI', NULL, 'es-EC', 'RUC no autorizado',
   'El RUC del emisor no tiene autorización para el ambiente seleccionado o el establecimiento/punto no coincide.',
   '["Confirme RUC y ambiente (pruebas/producción)","Revise establecimiento y punto de emisión","Actualice credenciales del certificado"]', 'error'),
  ('SII', 'RCL-CLIENTE-NIF-INVALIDO', 'es-ES', 'NIF del cliente inválido',
   'El NIF de la contraparte no supera la validación del SII.',
   '["Corrija el NIF en la ficha del cliente","Regenere y reenvíe el registro al SII"]', 'error'),
  ('SII', NULL, 'es-ES', 'Registro duplicado',
   'El registro ya fue enviado previamente para ese período.',
   '["No reenvíe duplicados","Si hay cambios, genere registro de modificación/corrección"]', 'warning')
ON CONFLICT DO NOTHING;

COMMIT;
