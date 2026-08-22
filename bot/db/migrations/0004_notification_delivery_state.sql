-- Migration 0004: حالة تسليم الإشعارات للحجز الذري وإعادة المحاولة.
-- القيم الحالية تمثل إشعارات وصلت بالفعل، لذا تكون حالتها sent افتراضيًا.

ALTER TABLE sent_notifications
    ADD COLUMN status TEXT NOT NULL DEFAULT 'sent'
    CHECK (status IN ('processing', 'sent', 'failed'));

ALTER TABLE sent_notifications
    ADD COLUMN claimed_at TEXT;

ALTER TABLE sent_notifications
    ADD COLUMN attempts INTEGER NOT NULL DEFAULT 1;

ALTER TABLE sent_notifications
    ADD COLUMN last_error TEXT;

CREATE INDEX IF NOT EXISTS idx_sent_notification_state
    ON sent_notifications(status, claimed_at);
