-- Create DB-backed rules that reserve sector_field_defaults for field/UI config only.
-- Then remove legacy non-UI rows that match those rules.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ui_field_config_scope_rules (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_type   VARCHAR(32)  NOT NULL,
    scope_value  VARCHAR(255) NOT NULL,
    action       VARCHAR(16)  NOT NULL DEFAULT 'deny',
    reason       TEXT,
    active       BOOLEAN      NOT NULL DEFAULT TRUE,
    UNIQUE (scope_type, scope_value)
);

ALTER TABLE ui_field_config_scope_rules
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

CREATE INDEX IF NOT EXISTS ix_ui_field_config_scope_rules_scope_type
    ON ui_field_config_scope_rules (scope_type);

CREATE INDEX IF NOT EXISTS ix_ui_field_config_scope_rules_scope_value
    ON ui_field_config_scope_rules (scope_value);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ui_field_config_scope_rules_scope
    ON ui_field_config_scope_rules (scope_type, scope_value);

INSERT INTO ui_field_config_scope_rules (scope_type, scope_value, action, reason, active)
VALUES
    (
        'sector_exact',
        '_system',
        'deny',
        'Namespace reservado para configuracion no-UI del sistema.',
        TRUE
    ),
    (
        'module_prefix',
        'importador.',
        'deny',
        'El runtime del importador no debe vivir en field-config UI.',
        TRUE
    )
ON CONFLICT (scope_type, scope_value) DO UPDATE
SET action = EXCLUDED.action,
    reason = EXCLUDED.reason,
    active = EXCLUDED.active;

DELETE FROM sector_field_defaults sfd
USING ui_field_config_scope_rules rules
WHERE rules.active = TRUE
  AND rules.action = 'deny'
  AND (
      (rules.scope_type = 'sector_exact' AND lower(sfd.sector) = lower(rules.scope_value))
      OR (
          rules.scope_type = 'module_prefix'
          AND lower(sfd.module) LIKE lower(rules.scope_value) || '%'
      )
  );

COMMIT;
