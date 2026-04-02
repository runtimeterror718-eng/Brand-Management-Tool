-- Telegram MVP schema for channel discovery + monitoring.
-- Safe to run multiple times.

BEGIN;

CREATE TABLE IF NOT EXISTS public.telegram_channels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id uuid NULL,
    channel_id text NOT NULL,
    channel_username text NULL,
    channel_title text NULL,
    channel_type text NULL,
    discovery_keyword text NULL,
    discovery_source text NULL DEFAULT 'keyword_search',
    channel_metadata jsonb NULL,
    llm_classification_response jsonb NULL,
    classification_label text NOT NULL DEFAULT 'irrelevant',
    should_monitor boolean NOT NULL DEFAULT false,
    last_checked_at timestamptz NULL,
    last_message_id text NULL,
    last_message_timestamp timestamptz NULL,
    first_discovered_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    raw_data jsonb NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_channels_brand_channel_unique
    ON public.telegram_channels (brand_id, channel_id);

CREATE INDEX IF NOT EXISTS idx_telegram_channels_should_monitor
    ON public.telegram_channels (should_monitor);

CREATE INDEX IF NOT EXISTS idx_telegram_channels_classification_label
    ON public.telegram_channels (classification_label);

CREATE INDEX IF NOT EXISTS idx_telegram_channels_discovery_keyword
    ON public.telegram_channels (discovery_keyword);

CREATE INDEX IF NOT EXISTS idx_telegram_channels_last_checked_at
    ON public.telegram_channels (last_checked_at);

ALTER TABLE public.telegram_messages
    ADD COLUMN IF NOT EXISTS telegram_channel_id uuid NULL,
    ADD COLUMN IF NOT EXISTS channel_username text NULL,
    ADD COLUMN IF NOT EXISTS discovery_keyword text NULL,
    ADD COLUMN IF NOT EXISTS discovery_source text NULL DEFAULT 'keyword_search',
    ADD COLUMN IF NOT EXISTS media_metadata jsonb NULL,
    ADD COLUMN IF NOT EXISTS llm_analysis_response jsonb NULL,
    ADD COLUMN IF NOT EXISTS risk_label text NULL,
    ADD COLUMN IF NOT EXISTS risk_score double precision NULL,
    ADD COLUMN IF NOT EXISTS is_suspicious boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS risk_flags jsonb NULL,
    ADD COLUMN IF NOT EXISTS analyzed_at timestamptz NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_messages_brand_channel_message_unique
    ON public.telegram_messages (brand_id, channel_id, message_id);

CREATE INDEX IF NOT EXISTS idx_telegram_messages_telegram_channel_id
    ON public.telegram_messages (telegram_channel_id);

CREATE INDEX IF NOT EXISTS idx_telegram_messages_channel_message_timestamp
    ON public.telegram_messages (channel_id, message_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_telegram_messages_is_suspicious
    ON public.telegram_messages (is_suspicious);

CREATE INDEX IF NOT EXISTS idx_telegram_messages_analyzed_at
    ON public.telegram_messages (analyzed_at);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_telegram_messages_channel_row'
    ) THEN
        ALTER TABLE public.telegram_messages
            ADD CONSTRAINT fk_telegram_messages_channel_row
            FOREIGN KEY (telegram_channel_id)
            REFERENCES public.telegram_channels(id)
            ON DELETE SET NULL;
    END IF;
END $$;

COMMIT;
