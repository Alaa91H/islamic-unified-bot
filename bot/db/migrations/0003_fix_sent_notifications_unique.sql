-- Migration 0003: اجعل منع التكرار يميز بين المستخدم والمجموعة.
-- كان القيد القديم لا يشمل target_type رغم أن المستودع يعتمد عليه.

CREATE TABLE IF NOT EXISTS sent_notifications_new (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id    INTEGER NOT NULL,
    target_type  TEXT NOT NULL CHECK (target_type IN ('user','group')),
    prayer       TEXT NOT NULL,
    prayer_date  TEXT NOT NULL,
    sent_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(target_id, target_type, prayer, prayer_date)
);

INSERT OR IGNORE INTO sent_notifications_new
    (id, target_id, target_type, prayer, prayer_date, sent_at)
SELECT id, target_id, target_type, prayer, prayer_date, sent_at
FROM sent_notifications;

DROP TABLE sent_notifications;

ALTER TABLE sent_notifications_new RENAME TO sent_notifications;

CREATE INDEX IF NOT EXISTS idx_sent_lookup
    ON sent_notifications(target_id, target_type, prayer, prayer_date);
