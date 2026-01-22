CREATE TABLE IF NOT EXISTS birthday_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    birth_date TEXT NOT NULL,
    calendar_type TEXT NOT NULL DEFAULT 'solar',
    note TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
