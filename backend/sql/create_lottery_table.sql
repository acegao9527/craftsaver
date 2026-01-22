-- 创建抽奖报名表
CREATE TABLE IF NOT EXISTS lottery_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
