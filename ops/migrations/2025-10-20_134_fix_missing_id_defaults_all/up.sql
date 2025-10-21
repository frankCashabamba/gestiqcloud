-- Restore auto-increment defaults for integer PK 'id' columns in public schema
DO $$
DECLARE
  r RECORD;
  seqname text;
  maxid bigint;
BEGIN
  FOR r IN
    SELECT kcu.table_schema,
           kcu.table_name,
           kcu.column_name,
           c.data_type,
           c.is_identity,
           c.identity_generation,
           c.column_default
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    JOIN information_schema.columns c
      ON c.table_schema = kcu.table_schema
     AND c.table_name  = kcu.table_name
     AND c.column_name = kcu.column_name
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND kcu.column_name = 'id'
      AND kcu.table_schema = 'public'
      AND c.data_type IN ('integer','bigint')
  LOOP
    -- Skip if already identity or has nextval default
    IF (r.is_identity IS NOT NULL AND r.is_identity = 'YES') OR (r.column_default IS NOT NULL AND position('nextval' in r.column_default) > 0) THEN
      CONTINUE;
    END IF;

    seqname := r.table_name || '_id_seq';
    BEGIN
      EXECUTE format('CREATE SEQUENCE IF NOT EXISTS public.%I OWNED BY %I.%I', seqname, r.table_name, r.column_name);
    EXCEPTION WHEN others THEN
      -- ignore
      NULL;
    END;
    BEGIN
      EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN %I SET DEFAULT nextval(%L)', r.table_schema, r.table_name, r.column_name, 'public.'||seqname);
    EXCEPTION WHEN others THEN
      -- ignore
      NULL;
    END;
    BEGIN
      EXECUTE format('SELECT COALESCE(MAX(%I),0)+1 FROM %I.%I', r.column_name, r.table_schema, r.table_name) INTO maxid;
      EXECUTE format('SELECT setval(%L, %s, false)', 'public.'||seqname, maxid::text);
    EXCEPTION WHEN others THEN
      -- ignore
      NULL;
    END;
  END LOOP;
END $$;

