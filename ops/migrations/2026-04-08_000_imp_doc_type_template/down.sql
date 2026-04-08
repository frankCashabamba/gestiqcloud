-- Rollback: imp_doc_type_template
DROP TRIGGER IF EXISTS trg_imp_doc_type_template_updated_at ON imp_doc_type_template;
DROP FUNCTION IF EXISTS _set_imp_doc_type_template_updated_at();
DROP TABLE IF EXISTS imp_doc_type_template;
