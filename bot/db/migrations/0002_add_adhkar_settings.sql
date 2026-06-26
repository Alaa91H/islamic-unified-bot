-- Migration 0002: إعدادات الأذكار لكل مجموعة
-- جدول adhkar_settings يخزّن تفضيلات الأذكار لكل مجموعة.
-- كل مجموعة يمكنها تمكين/تعطيل وتخصيص توقيت الأذكار.

CREATE TABLE IF NOT EXISTS adhkar_settings (
    chat_id              INTEGER PRIMARY KEY,
    interval_enabled     INTEGER NOT NULL DEFAULT 0 CHECK (interval_enabled IN (0,1)),
    interval_minutes     INTEGER NOT NULL DEFAULT 20 CHECK (interval_minutes >= 1),
    morning_enabled      INTEGER NOT NULL DEFAULT 0 CHECK (morning_enabled IN (0,1)),
    morning_time         TEXT    NOT NULL DEFAULT '06:00',
    evening_enabled      INTEGER NOT NULL DEFAULT 0 CHECK (evening_enabled IN (0,1)),
    evening_time         TEXT    NOT NULL DEFAULT '18:00',
    friday_enabled       INTEGER NOT NULL DEFAULT 0 CHECK (friday_enabled IN (0,1)),
    friday_time          TEXT    NOT NULL DEFAULT '10:00',
    last_adhkar_category TEXT,
    last_sent_at         TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS adhkar_sent (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id   INTEGER NOT NULL,
    sent_key  TEXT NOT NULL,
    sent_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(chat_id, sent_key)
);
