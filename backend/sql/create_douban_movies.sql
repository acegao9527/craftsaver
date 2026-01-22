-- 创建豆瓣电影表
CREATE TABLE IF NOT EXISTS douban_movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    douban_id VARCHAR(32) UNIQUE NOT NULL,
    title VARCHAR(256) NOT NULL,
    original_title VARCHAR(256),
    rating FLOAT,                       -- 个人评分（0-5星）
    rating_star VARCHAR(16),            -- 个人评分星级标记
    original_rating FLOAT,              -- 电影原始评分（豆瓣评分）
    original_rating_star VARCHAR(16),   -- 原始评分星级标记
    date_added VARCHAR(32),             -- 观看/添加日期
    comment TEXT,                       -- 个人短评
    tags VARCHAR(256),
    status VARCHAR(16),                 -- 状态：想看/在看/已看
    cover_url VARCHAR(512),
    directors VARCHAR(256),
    actors VARCHAR(512),
    year INTEGER,
    country VARCHAR(128),
    genre VARCHAR(128),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_douban_movies_douban_id ON douban_movies(douban_id);
CREATE INDEX IF NOT EXISTS idx_douban_movies_date_added ON douban_movies(date_added);
CREATE INDEX IF NOT EXISTS idx_douban_movies_rating ON douban_movies(rating);
CREATE INDEX IF NOT EXISTS idx_douban_movies_original_rating ON douban_movies(original_rating);
CREATE INDEX IF NOT EXISTS idx_douban_movies_year ON douban_movies(year);
CREATE INDEX IF NOT EXISTS idx_douban_movies_genre ON douban_movies(genre);
CREATE INDEX IF NOT EXISTS idx_douban_movies_status ON douban_movies(status);
