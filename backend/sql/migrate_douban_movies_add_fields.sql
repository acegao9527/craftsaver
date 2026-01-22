-- 豆瓣电影表迁移脚本
-- 添加原始评分、状态字段

-- 添加新列（如果不存在）
ALTER TABLE douban_movies ADD COLUMN original_rating FLOAT;
ALTER TABLE douban_movies ADD COLUMN original_rating_star VARCHAR(16);
ALTER TABLE douban_movies ADD COLUMN status VARCHAR(16);

-- 更新现有数据的状态（根据现有数据特征设置默认值）
UPDATE douban_movies SET status = '已看' WHERE status IS NULL;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_douban_movies_original_rating ON douban_movies(original_rating);
CREATE INDEX IF NOT EXISTS idx_douban_movies_status ON douban_movies(status);
