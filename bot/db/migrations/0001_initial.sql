-- Migration 0001: المخطط الأولي
-- جداول: user_settings, group_settings, sent_notifications, schema_version

CREATE TABLE IF NOT EXISTS user_settings (
    user_id           INTEGER PRIMARY KEY,
    city              TEXT NOT NULL,
    method            TEXT NOT NULL DEFAULT 'isna'
                      CHECK (method IN ('karachi','makkah','isna','egypt','algiers','dubai')),
    asr_method        TEXT NOT NULL DEFAULT 'standard'
                      CHECK (asr_method IN ('standard','hanafi')),
    timezone          INTEGER NOT NULL DEFAULT 0,
    language          TEXT NOT NULL DEFAULT 'ar',
    notifications_on  INTEGER NOT NULL DEFAULT 1 CHECK (notifications_on IN (0,1)),
    prelude_on        INTEGER NOT NULL DEFAULT 0 CHECK (prelude_on IN (0,1)),
    prelude_minutes   INTEGER NOT NULL DEFAULT 5 CHECK (prelude_minutes >= 0),
    enabled_prayers   TEXT NOT NULL DEFAULT '["fajr","dhuhr","asr","maghrib","isha"]',
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_user_notif
    ON user_settings(notifications_on) WHERE notifications_on = 1;

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id               INTEGER PRIMARY KEY,
    city                  TEXT NOT NULL,
    method                TEXT NOT NULL DEFAULT 'isna'
                          CHECK (method IN ('karachi','makkah','isna','egypt','algiers','dubai')),
    asr_method            TEXT NOT NULL DEFAULT 'standard'
                          CHECK (asr_method IN ('standard','hanafi')),
    azan_source           TEXT NOT NULL DEFAULT 'traditional',
    stream_quran_on       INTEGER NOT NULL DEFAULT 0 CHECK (stream_quran_on IN (0,1)),
    stop_stream_before_min INTEGER NOT NULL DEFAULT 0,
    linked_user_id        INTEGER,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sent_notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id    INTEGER NOT NULL,
    target_type  TEXT NOT NULL CHECK (target_type IN ('user','group')),
    prayer       TEXT NOT NULL,
    prayer_date  TEXT NOT NULL,
    sent_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(target_id, prayer, prayer_date)
);
CREATE INDEX IF NOT EXISTS idx_sent_lookup
    ON sent_notifications(target_id, prayer, prayer_date);

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
