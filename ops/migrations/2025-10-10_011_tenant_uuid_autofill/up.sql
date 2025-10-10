-- Ensure pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Strict helper: raises if tenant GUC is not set
CREATE OR REPLACE FUNCTION current_tenant_uuid() RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    v text;
BEGIN
    v := current_setting('app.tenant_id', true);
    IF v IS NULL OR v = '' THEN
        RAISE EXCEPTION 'app.tenant_id GUC is not set';
    END IF;
    RETURN v::uuid;
END;
$$;

-- Trigger to auto-fill tenant_id from GUC if missing
CREATE OR REPLACE FUNCTION set_tenant_id() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.tenant_id IS NULL THEN
        NEW.tenant_id := current_tenant_uuid();
    END IF;
    RETURN NEW;
END;
$$;

-- Normalize tenant_id columns to UUID and attach auto-fill trigger
DO $$
DECLARE
    r record;
    trg_name text;
BEGIN
    FOR r IN
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND column_name = 'tenant_id'
    LOOP
        -- Cast to UUID if needed
        BEGIN
            EXECUTE format(
                'ALTER TABLE %I.%I ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid',
                r.table_schema, r.table_name
            );
        EXCEPTION WHEN others THEN
            -- ignore if already uuid or cast not needed
            NULL;
        END;

        -- Ensure NOT NULL
        BEGIN
            EXECUTE format(
                'ALTER TABLE %I.%I ALTER COLUMN tenant_id SET NOT NULL',
                r.table_schema, r.table_name
            );
        EXCEPTION WHEN others THEN
            NULL;
        END;

        -- Attach trigger if not present
        trg_name := 'trg_set_tenant_id_' || r.table_name;
        EXECUTE format(
            $$DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = %L
                ) THEN
                    CREATE TRIGGER %I
                    BEFORE INSERT ON %I.%I
                    FOR EACH ROW EXECUTE FUNCTION set_tenant_id();
                END IF;
            END $$;$$,
            trg_name, trg_name, r.table_schema, r.table_name
        );
    END LOOP;
END $$;

-- Ensure UUID defaults for PKs we manage via ORM (example: stock_moves)
ALTER TABLE IF EXISTS public.stock_moves
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

