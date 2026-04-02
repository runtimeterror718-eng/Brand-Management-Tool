-- Telegram metadata cleanup:
-- 1) keep is_fake/is_scam NULL (LLM-owned),
-- 2) drop legacy channel_metadata column now that metadata is split.
-- Safe to run multiple times.

BEGIN;

UPDATE public.telegram_channels
SET
    is_fake = NULL,
    is_scam = NULL,
    updated_at = NOW()
WHERE is_fake IS NOT NULL OR is_scam IS NOT NULL;

ALTER TABLE public.telegram_channels
    DROP COLUMN IF EXISTS channel_metadata;

COMMIT;
