BEGIN;

DROP INDEX IF EXISTS ix_printer_label_configurations_printer_port;
DROP INDEX IF EXISTS ix_printer_label_configurations_tenant_id;
DROP TABLE IF EXISTS printer_label_configurations;

COMMIT;
