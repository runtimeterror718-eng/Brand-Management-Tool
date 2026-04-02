-- Telegram channel metadata split + backfill.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ADD COLUMN IF NOT EXISTS public_url text NULL,
    ADD COLUMN IF NOT EXISTS is_verified boolean NULL,
    ADD COLUMN IF NOT EXISTS is_scam boolean NULL,
    ADD COLUMN IF NOT EXISTS is_fake boolean NULL,
    ADD COLUMN IF NOT EXISTS participants_count integer NULL,
    ADD COLUMN IF NOT EXISTS live_test boolean NULL,
    ADD COLUMN IF NOT EXISTS live_test_run_at timestamptz NULL;

-- Discovery mode should leave classification fields empty until LLM/heuristic classification runs.
ALTER TABLE public.telegram_channels
    ALTER COLUMN classification_label DROP NOT NULL,
    ALTER COLUMN classification_label DROP DEFAULT;

-- One-shot backfill from legacy JSON metadata.
UPDATE public.telegram_channels
SET
    public_url = COALESCE(
        public_url,
        NULLIF(channel_metadata ->> 'public_url', '')
    ),
    is_verified = COALESCE(
        is_verified,
        CASE
            WHEN channel_metadata ? 'is_verified' THEN (channel_metadata ->> 'is_verified')::boolean
            ELSE NULL
        END
    ),
    is_scam = COALESCE(
        is_scam,
        CASE
            WHEN channel_metadata ? 'is_scam' THEN (channel_metadata ->> 'is_scam')::boolean
            ELSE NULL
        END
    ),
    is_fake = COALESCE(
        is_fake,
        CASE
            WHEN channel_metadata ? 'is_fake' THEN (channel_metadata ->> 'is_fake')::boolean
            ELSE NULL
        END
    ),
    participants_count = COALESCE(
        participants_count,
        CASE
            WHEN channel_metadata ? 'participants_count'
                 AND (channel_metadata ->> 'participants_count') ~ '^-?[0-9]+$'
            THEN (channel_metadata ->> 'participants_count')::integer
            ELSE NULL
        END
    ),
    live_test = COALESCE(
        live_test,
        CASE
            WHEN channel_metadata ? 'live_test' THEN (channel_metadata ->> 'live_test')::boolean
            ELSE NULL
        END
    ),
    live_test_run_at = COALESCE(
        live_test_run_at,
        CASE
            WHEN channel_metadata ? 'live_test_run_at'
                 AND NULLIF(channel_metadata ->> 'live_test_run_at', '') IS NOT NULL
            THEN (channel_metadata ->> 'live_test_run_at')::timestamptz
            ELSE NULL
        END
    ),
    updated_at = NOW()
WHERE channel_metadata IS NOT NULL;

-- For pre-classification discovery rows, keep classification fields empty.
UPDATE public.telegram_channels
SET
    classification_label = NULL,
    llm_classification_response = NULL,
    should_monitor = FALSE,
    updated_at = NOW()
WHERE (llm_classification_response IS NULL OR llm_classification_response = '{}'::jsonb)
  AND COALESCE(classification_label, '') = 'irrelevant';

COMMIT;
