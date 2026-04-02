-- Telegram message-analysis rollup persistence.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.telegram_channels
    ADD COLUMN IF NOT EXISTS message_risk_rollup jsonb NULL,
    ADD COLUMN IF NOT EXISTS message_risk_rollup_at timestamptz NULL;

CREATE INDEX IF NOT EXISTS idx_telegram_messages_risk_label
    ON public.telegram_messages (risk_label);

COMMIT;
