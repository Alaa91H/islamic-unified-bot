-- Migration 0005: جدولة إعادة محاولة outbox لإشعارات الصلاة.
ALTER TABLE sent_notifications
    ADD COLUMN next_retry_at TEXT;

ALTER TABLE sent_notifications
    ADD COLUMN retry_class TEXT NOT NULL DEFAULT 'transient'
    CHECK (retry_class IN ('transient', 'permanent'));

CREATE INDEX IF NOT EXISTS idx_sent_notifications_retry
    ON sent_notifications(status, next_retry_at);
