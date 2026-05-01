-- Migration: imp_doc_type_template
-- Plantillas de extracción por tipo de documento sin llamada a AI.
-- Capa L5 del pre-clasificador: si el sistema ya conoce el patrón de un
-- tipo de documento (regexes, label_search), extrae los campos directamente
-- evitando llamadas a Ollama para documentos que se repiten con frecuencia.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS imp_doc_type_template (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    -- NULL = template global (disponible para todos los tenants)

    doc_type                    TEXT NOT NULL,
    -- Tipo de documento canónico: INVOICE, RECEIPT, PAYROLL, etc.

    nombre                      TEXT NOT NULL,
    -- Nombre descriptivo para UI/admin, ej: "Factura proveedor Perú"

    activo                      BOOLEAN NOT NULL DEFAULT TRUE,
    prioridad                   INTEGER NOT NULL DEFAULT 0,
    -- Mayor prioridad = se evalúa primero dentro del mismo doc_type

    -- ── Parámetros de activación ─────────────────────────────────────────
    -- Condiciones que deben cumplirse para aplicar este template.
    -- Todos los campos presentes son AND (deben cumplirse todos).
    activacion_json             JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "filename_patterns": ["factura_*", "*_inv_*"],   -- regex contra stem del filename
    --   "text_keywords": ["ruc", "igv", "sunat"],        -- todas deben estar en texto OCR
    --   "min_text_length": 100,                          -- mínimo de caracteres OCR
    --   "tipo_archivo": ["PDF", "JPG", "PNG"]            -- restringir a tipos de archivo
    -- }

    -- ── Reglas de extracción ─────────────────────────────────────────────
    -- Cómo extraer cada campo canónico.
    extraccion_json             JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "fields": {
    --     "doc_number": {
    --       "regex": ["(?:F|E)-?\\d{3}-\\d+", "N[°ú]\\.?\\s*(\\S+)"],
    --       "label_search": ["número de comprobante", "n° factura", "serie"],
    --       "tipo": "text",
    --       "required": true
    --     },
    --     "total_amount": {
    --       "regex": ["TOTAL\\s+(?:A PAGAR)?\\s*S?/?\\.?\\s*([\\d,\\.]+)"],
    --       "label_search": ["total a pagar", "importe total", "total general"],
    --       "tipo": "decimal"
    --     },
    --     "issue_date": {
    --       "regex": ["(\\d{2}[/-]\\d{2}[/-]\\d{2,4})"],
    --       "label_search": ["fecha de emisión", "fecha", "emitido el"],
    --       "tipo": "date"
    --     },
    --     "vendor": {
    --       "label_search": ["razón social", "nombre del emisor", "proveedor"],
    --       "tipo": "text"
    --     }
    --   },
    --   "line_items": {
    --     "column_map": {
    --       "descripcion": ["descripción", "producto", "item", "concepto"],
    --       "cantidad":    ["cantidad", "cant", "qty", "unidades"],
    --       "precio_unitario": ["precio unit.", "p.u.", "valor unit.", "unit price"],
    --       "total": ["total", "importe", "subtotal línea"]
    --     }
    --   }
    -- }

    -- ── Control de calidad ────────────────────────────────────────────────
    min_confidence_para_skip    FLOAT NOT NULL DEFAULT 0.80,
    -- Si la extracción por template alcanza esta confianza, NO se llama a AI.
    -- Si la confianza es menor, el template aporta hints pero AI sigue ejecutándose.

    campos_requeridos           TEXT[] NOT NULL DEFAULT '{}',
    -- Si alguno de estos campos falta tras la extracción, baja a confianza 0
    -- y se vuelve a AI como fallback.

    -- ── Stats de uso ─────────────────────────────────────────────────────
    total_usos                  INTEGER NOT NULL DEFAULT 0,
    total_exitosos              INTEGER NOT NULL DEFAULT 0,
    -- exitoso = usuario confirmó sin editar campos del template
    last_used_at                TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index principal: búsqueda por tenant + tipo activo + prioridad
ALTER TABLE imp_doc_type_template
    ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE imp_doc_type_template
    ALTER COLUMN activo SET DEFAULT TRUE;
ALTER TABLE imp_doc_type_template
    ALTER COLUMN prioridad SET DEFAULT 0;
ALTER TABLE imp_doc_type_template
    ALTER COLUMN activacion_json SET DEFAULT '{}';
ALTER TABLE imp_doc_type_template
    ALTER COLUMN extraccion_json SET DEFAULT '{}';
ALTER TABLE imp_doc_type_template
    ALTER COLUMN min_confidence_para_skip SET DEFAULT 0.80;
ALTER TABLE imp_doc_type_template
    ALTER COLUMN campos_requeridos SET DEFAULT '{}';
ALTER TABLE imp_doc_type_template
    ALTER COLUMN total_usos SET DEFAULT 0;
ALTER TABLE imp_doc_type_template
    ALTER COLUMN total_exitosos SET DEFAULT 0;
ALTER TABLE imp_doc_type_template
    ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE imp_doc_type_template
    ALTER COLUMN updated_at SET DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_imp_doc_type_template_tenant_type
    ON imp_doc_type_template (tenant_id, doc_type, activo, prioridad DESC);

-- Index para templates globales (tenant_id IS NULL)
CREATE INDEX IF NOT EXISTS idx_imp_doc_type_template_global
    ON imp_doc_type_template (doc_type, activo, prioridad DESC)
    WHERE tenant_id IS NULL;

-- ── Trigger: actualizar updated_at automáticamente ───────────────────────────
CREATE OR REPLACE FUNCTION _set_imp_doc_type_template_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_imp_doc_type_template_updated_at ON imp_doc_type_template;
CREATE TRIGGER trg_imp_doc_type_template_updated_at
    BEFORE UPDATE ON imp_doc_type_template
    FOR EACH ROW EXECUTE FUNCTION _set_imp_doc_type_template_updated_at();

-- ── Seeds globales de templates comunes ─────────────────────────────────────
-- Facturas de proveedores (formato Perú / SUNAT)
INSERT INTO imp_doc_type_template (
    tenant_id, doc_type, nombre, prioridad,
    activacion_json, extraccion_json,
    min_confidence_para_skip, campos_requeridos
) VALUES (
    NULL,
    'INVOICE',
    'Factura proveedor - formato SUNAT/Perú',
    10,
    '{
        "text_keywords": ["ruc", "sunat"],
        "tipo_archivo": ["PDF", "JPG", "PNG", "IMG"]
    }',
    '{
        "fields": {
            "doc_number": {
                "regex": ["([A-Z]{1,2}[0-9]{3}-[0-9]{1,8})", "(?:FACT|FAC|F)[.\\s]*N[°o.]?[\\s]*(\\S{3,15})"],
                "label_search": ["número de comprobante", "n° factura", "serie y correlativo", "número"],
                "tipo": "text",
                "required": true
            },
            "issue_date": {
                "regex": ["(\\d{2}[/\\-]\\d{2}[/\\-]\\d{4})", "(\\d{4}[/\\-]\\d{2}[/\\-]\\d{2})"],
                "label_search": ["fecha de emisión", "fecha de emision", "fecha emisión", "fecha"],
                "tipo": "date",
                "required": true
            },
            "vendor_tax_id": {
                "regex": ["\\b(20\\d{9}|10\\d{9})\\b"],
                "label_search": ["ruc del emisor", "ruc proveedor", "ruc"],
                "tipo": "text"
            },
            "vendor": {
                "label_search": ["razón social del emisor", "nombre del proveedor", "emisor", "razón social"],
                "tipo": "text"
            },
            "total_amount": {
                "regex": ["TOTAL\\s*(?:A PAGAR|GENERAL)?\\s*S?/?\\.?\\s*([\\d,\\.]+)", "TOTAL\\s+([\\d,\\.]+)"],
                "label_search": ["total a pagar", "importe total", "total general", "precio total", "total"],
                "tipo": "decimal",
                "required": true
            },
            "subtotal": {
                "regex": ["OP\\.?\\s*GRAVADA\\s+([\\d,\\.]+)", "BASE\\s+IMPONIBLE\\s+([\\d,\\.]+)", "SUBTOTAL\\s+([\\d,\\.]+)"],
                "label_search": ["op. gravada", "operación gravada", "base imponible", "subtotal"],
                "tipo": "decimal"
            },
            "tax_amount": {
                "regex": ["I\\.?G\\.?V\\.?\\s+([\\d,\\.]+)", "IGV\\s+([\\d,\\.]+)"],
                "label_search": ["igv", "i.g.v.", "impuesto general a las ventas"],
                "tipo": "decimal"
            },
            "currency": {
                "regex": ["(USD|PEN|EUR|S/\\.|\\$)"],
                "label_search": ["moneda", "currency"],
                "tipo": "text"
            }
        },
        "line_items": {
            "column_map": {
                "descripcion": ["descripción", "descripcion", "producto", "bien o servicio", "concepto"],
                "cantidad": ["cantidad", "cant.", "qty", "unidades"],
                "unidad": ["unidad", "und.", "u.m.", "um"],
                "precio_unitario": ["precio unit.", "p.u.", "valor unitario", "precio unitario"],
                "total": ["total", "importe", "precio total", "valor total"]
            }
        }
    }',
    0.75,
    ARRAY['doc_number', 'issue_date', 'total_amount']
);

-- Recibos / Boletas (simples, sin IGV detallado)
INSERT INTO imp_doc_type_template (
    tenant_id, doc_type, nombre, prioridad,
    activacion_json, extraccion_json,
    min_confidence_para_skip, campos_requeridos
) VALUES (
    NULL,
    'RECEIPT',
    'Boleta de venta / Recibo simple',
    10,
    '{
        "text_keywords": ["boleta"],
        "tipo_archivo": ["PDF", "JPG", "PNG", "IMG"]
    }',
    '{
        "fields": {
            "doc_number": {
                "regex": ["([B][0-9]{3}-[0-9]{1,8})", "(?:BOL|B)[.\\s]*N[°o.]?[\\s]*(\\S{3,15})"],
                "label_search": ["número de boleta", "n° boleta", "boleta n°", "número"],
                "tipo": "text",
                "required": true
            },
            "issue_date": {
                "regex": ["(\\d{2}[/\\-]\\d{2}[/\\-]\\d{4})", "(\\d{4}[/\\-]\\d{2}[/\\-]\\d{2})"],
                "label_search": ["fecha de emisión", "fecha"],
                "tipo": "date",
                "required": true
            },
            "total_amount": {
                "regex": ["TOTAL\\s+([\\d,\\.]+)", "IMPORTE\\s+([\\d,\\.]+)"],
                "label_search": ["total", "importe total", "total a pagar"],
                "tipo": "decimal",
                "required": true
            },
            "vendor": {
                "label_search": ["razón social", "emisor", "nombre"],
                "tipo": "text"
            }
        }
    }',
    0.70,
    ARRAY['doc_number', 'total_amount']
);

-- Extractos bancarios
INSERT INTO imp_doc_type_template (
    tenant_id, doc_type, nombre, prioridad,
    activacion_json, extraccion_json,
    min_confidence_para_skip, campos_requeridos
) VALUES (
    NULL,
    'BANK_STATEMENT',
    'Extracto bancario genérico',
    5,
    '{
        "text_keywords": ["cuenta", "saldo"],
        "min_text_length": 300,
        "tipo_archivo": ["PDF", "XLSX", "CSV"]
    }',
    '{
        "fields": {
            "doc_number": {
                "label_search": ["número de cuenta", "n° cuenta", "cuenta corriente", "cuenta"],
                "tipo": "text"
            },
            "issue_date": {
                "regex": ["(?:periodo|period)\\s*:?\\s*(\\d{2}[/\\-]\\d{2}[/\\-]\\d{4})", "(\\d{4}[/\\-]\\d{2}[/\\-]\\d{2})"],
                "label_search": ["período", "periodo", "fecha"],
                "tipo": "date"
            },
            "vendor": {
                "label_search": ["banco", "entidad financiera", "institución"],
                "tipo": "text"
            },
            "total_amount": {
                "regex": ["saldo\\s+(?:final|actual|disponible)\\s+([\\d,\\.]+)"],
                "label_search": ["saldo final", "saldo actual", "saldo disponible", "saldo"],
                "tipo": "decimal"
            }
        },
        "line_items": {
            "column_map": {
                "issue_date": ["fecha", "date", "fecha operación"],
                "descripcion": ["descripción", "descripcion", "concepto", "detalle", "operación"],
                "total": ["monto", "importe", "cargo", "abono", "amount"]
            }
        }
    }',
    0.65,
    ARRAY[]::TEXT[]
);
