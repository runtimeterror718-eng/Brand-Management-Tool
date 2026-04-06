-- Add description + creator columns for discovery metadata.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ADD COLUMN IF NOT EXISTS channel_description text NULL,
    ADD COLUMN IF NOT EXISTS creator_id text NULL,
    ADD COLUMN IF NOT EXISTS creator_username text NULL;

UPDATE public.telegram_channels
SET
    channel_description = COALESCE(
        channel_description,
        NULLIF(raw_data -> 'discovery_metadata' ->> 'channel_description', ''),
        NULLIF(raw_data -> 'discovery_metadata' ->> 'about', '')
    ),
    creator_id = COALESCE(
        creator_id,
        NULLIF(raw_data -> 'discovery_metadata' ->> 'creator_id', '')
    ),
    creator_username = COALESCE(
        creator_username,
        NULLIF(raw_data -> 'discovery_metadata' ->> 'creator_username', '')
    ),
    updated_at = NOW()
WHERE raw_data IS NOT NULL;

COMMIT;
