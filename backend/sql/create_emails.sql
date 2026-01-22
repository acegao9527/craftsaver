-- 邮件账号配置表
CREATE TABLE IF NOT EXISTS email_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account VARCHAR(255) UNIQUE NOT NULL,
    imap_server VARCHAR(255) NOT NULL,
    imap_port INTEGER NOT NULL DEFAULT 993,
    authorization_code TEXT NOT NULL,
    folder VARCHAR(100) DEFAULT 'INBOX',
    is_active INTEGER DEFAULT 1,
    last_uid INTEGER DEFAULT 0,
    last_uid_time INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- 邮件表
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_account VARCHAR(255) NOT NULL,
    uid VARCHAR(64) NOT NULL,
    subject VARCHAR(500),
    sender VARCHAR(255),
    sender_name VARCHAR(255),
    received_at INTEGER NOT NULL,
    preview TEXT,
    summary TEXT,
    importance VARCHAR(20) DEFAULT 'medium',
    action_items TEXT,  -- JSON 数组
    raw_content TEXT,
    created_at INTEGER DEFAULT (unixepoch()),
    UNIQUE(email_account, uid)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_emails_account ON emails(email_account);
CREATE INDEX IF NOT EXISTS idx_emails_received ON emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_uid ON emails(email_account, uid);
