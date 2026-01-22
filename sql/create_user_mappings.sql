-- 用户映射表：企微用户 ↔ Craft文档
CREATE TABLE IF NOT EXISTS user_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wecom_openid VARCHAR(128) NOT NULL,      -- 企微用户OpenID
    craft_link_id VARCHAR(128) NOT NULL,     -- Craft链接ID
    craft_document_id VARCHAR(128) NOT NULL, -- Craft文档ID
    craft_token VARCHAR(128) NOT NULL,       -- Craft文档Token
    display_name VARCHAR(128),               -- 显示名称
    is_enabled INTEGER DEFAULT 1,            -- 是否启用转发
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(wecom_openid)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_wecom_openid ON user_mappings(wecom_openid);
