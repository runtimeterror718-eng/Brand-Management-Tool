-- Add explicit channel fulfilment score/confidence columns.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ADD COLUMN IF NOT EXISTS fake_score_10 integer NULL,
    ADD COLUMN IF NOT EXISTS confidence double precision NULL;

ALTER TABLE public.telegram_channels
    DROP CONSTRAINT IF EXISTS telegram_channels_fake_score_10_check;

ALTER TABLE public.telegram_channels
    ADD CONSTRAINT telegram_channels_fake_score_10_check
    CHECK (
        fake_score_10 IS NULL
        OR (fake_score_10 >= 0 AND fake_score_10 <= 10)
    );

CREATE INDEX IF NOT EXISTS idx_telegram_channels_fake_score_10
    ON public.telegram_channels (fake_score_10);

COMMIT;
