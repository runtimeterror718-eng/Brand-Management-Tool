-- Telegram message-fetch schema updates:
-- 1) Channel historical ingestion flag.
-- 2) Message media storage columns (including base64 payload).
-- 3) Message uniqueness switch to username join key.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ADD COLUMN IF NOT EXISTS historical_data boolean NULL;

UPDATE public.telegram_channels
SET
    historical_data = FALSE,
    updated_at = NOW()
WHERE historical_data IS NULL;

CREATE INDEX IF NOT EXISTS idx_telegram_channels_historical_data
    ON public.telegram_channels (historical_data);

ALTER TABLE public.telegram_messages
    ADD COLUMN IF NOT EXISTS media_base64 text NULL,
    ADD COLUMN IF NOT EXISTS media_mime_type text NULL,
    ADD COLUMN IF NOT EXISTS media_file_name text NULL,
    ADD COLUMN IF NOT EXISTS media_file_size_bytes bigint NULL,
    ADD COLUMN IF NOT EXISTS media_downloaded_at timestamptz NULL;

UPDATE public.telegram_messages
SET channel_username = COALESCE(
    NULLIF(channel_username, ''),
    NULLIF(raw_data -> 'channel' ->> 'channel_username', '')
)
WHERE COALESCE(channel_username, '') = ''
  AND raw_data IS NOT NULL;

DROP INDEX IF EXISTS public.idx_telegram_messages_brand_channel_message_unique;

CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_messages_brand_channel_username_message_unique
    ON public.telegram_messages (brand_id, channel_username, message_id);

COMMIT;
