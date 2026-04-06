-- Drop creator fields; not reliably available from API for our use-case.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    DROP COLUMN IF EXISTS creator_id,
    DROP COLUMN IF EXISTS creator_username;

COMMIT;
