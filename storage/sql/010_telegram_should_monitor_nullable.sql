-- Make should_monitor nullable for discovery phase.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ALTER COLUMN should_monitor DROP NOT NULL,
    ALTER COLUMN should_monitor DROP DEFAULT;

UPDATE public.telegram_channels
SET
    should_monitor = NULL,
    updated_at = NOW()
WHERE should_monitor = FALSE;

COMMIT;
