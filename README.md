# CraftSaver - 企业微信消息同步工具

## 项目简介

CraftSaver 是一个将企业微信消息同步到 Craft 文档的工具，支持多种消息类型（文本、图片、链接、文件等）的自动处理和保存。

## 核心功能

- **企业微信消息同步**：使用官方 SDK 拉取消息存档，支持文本、图片、链接、视频、文件等消息类型
- **统一消息存储**：将消息统一存储到 SQLite 数据库
- **Craft 集成**：将消息智能转换为 Craft 原生块保存到文档

## 技术栈

- **语言**：Python 3.12
- **框架**：FastAPI + uvicorn
- **数据库**：SQLite
- **部署**：Docker + Docker Compose
- **集成**：企业微信消息归档、Craft 笔记

## 项目结构

```
CraftSaver/
├── docker-deploy.sh             # Docker 部署脚本
├── Dockerfile                   # Docker 构建文件
├── docker-compose.yml           # Docker Compose 配置
├── .env.example                 # 环境变量配置示例
├── .env                         # 环境变量
├── requirements.txt             # Python 依赖
├── main.py                      # 主入口 (FastAPI + 消息轮询)
├── src/                         # 源代码
│   ├── api/routers/             # API 路由
│   ├── handlers/                # 消息处理器
│   ├── models/                  # 数据模型
│   ├── services/                # 服务模块
│   ├── sql/                     # 数据库初始化脚本
│   └── utils/                   # 工具函数
├── lib/                         # 第三方库
│   ├── wework-x86_64/           # WeCom SDK (x86_64)
│   └── wework-arm64/            # WeCom SDK (ARM64)
└── data/                        # 数据存储目录
```

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```ini
# 企业微信
WECOM_TOKEN=your_wecom_token
WECOM_CORP_ID=your_corp_id
WECOM_ENCODING_AES_KEY=your_encoding_aes_key
WECOM_APP_SECRET=your_app_secret
WECOM_PRIVATE_KEY_PATH=private_key.pem

# 可选：过滤机器人自己发的消息
WECOM_BOT_USERID=your_bot_userid

# Craft 配置
CRAFT_API_TOKEN=your_craft_api_token
CRAFT_LINKS_ID=your_craft_links_id

# 可选：默认转发目标
DEFAULT_CRAFT_LINK_ID=
DEFAULT_CRAFT_DOCUMENT_ID=
DEFAULT_CRAFT_TOKEN=

# SQLite 数据库
SQLITE_DB_PATH=data/savehelper.db

# 应用端口
APP_PORT=8001

# 日志级别
LOG_LEVEL=INFO
```

### 2. Docker 部署

```bash
# 一键部署（包含构建、启动、健康检查）
./docker-deploy.sh

# 查看日志
docker logs -f craftsaver_app
```

### 3. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

## API 端点

- `GET /` - 健康检查
- `POST /craft/save` - 保存消息到 Craft
- `GET /craft/links` - 获取 Craft 链接列表

## 验证与测试

修改代码后必须运行 `./docker-deploy.sh` 重新构建并验证：

```bash
./docker-deploy.sh

# 验证服务
curl http://localhost:8001/

# 检查日志
docker logs craftsaver_app
```

## 环境变量说明

| 变量 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `WECOM_CORP_ID` | 企业ID | 是 | - |
| `WECOM_APP_SECRET` | 消息存档 Secret | 是 | - |
| `WECOM_TOKEN` | 回调 Token | 是 | - |
| `WECOM_ENCODING_AES_KEY` | 回调 AES Key | 是 | - |
| `CRAFT_API_TOKEN` | Craft API Token | 是 | - |
| `CRAFT_LINKS_ID` | Craft 文档 ID | 是 | - |
| `APP_PORT` | 应用端口 | 否 | 8001 |
| `SQLITE_DB_PATH` | SQLite 数据库文件路径 | 否 | data/savehelper.db |

## 许可证

MIT
