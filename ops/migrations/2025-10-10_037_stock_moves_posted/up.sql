-- Add posted flag to stock_moves and backfill based on tentative

ALTER TABLE public.stock_moves ADD COLUMN IF NOT EXISTS posted boolean NOT NULL DEFAULT false;

-- Backfill: mark as posted when not tentative (historical rows)
UPDATE public.stock_moves SET posted = TRUE WHERE tentative = FALSE;

-- Optional index to query posted vs tentative
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE indexname = 'ix_stock_moves_posted'
  ) THEN
    CREATE INDEX ix_stock_moves_posted ON public.stock_moves (posted);
  END IF;
END $$;

