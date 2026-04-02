-- Add channel activity columns.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ADD COLUMN IF NOT EXISTS channel_created_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS message_count_7d integer NULL;

-- Backfill created date from stored raw chat payload (if present).
UPDATE public.telegram_channels
SET
    channel_created_at = COALESCE(
        channel_created_at,
        CASE
            WHEN raw_data ? 'chat'
                 AND (raw_data -> 'chat') ? 'date'
                 AND NULLIF(raw_data -> 'chat' ->> 'date', '') IS NOT NULL
            THEN (raw_data -> 'chat' ->> 'date')::timestamptz
            ELSE NULL
        END
    ),
    updated_at = NOW()
WHERE raw_data IS NOT NULL;

COMMIT;
