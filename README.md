# SaveHelper - 企业微信消息同步工具

## 项目简介

SaveHelper 是一个将企业微信消息同步到 Craft 文档的工具，支持多种消息类型（文本、图片、链接、文件等）的自动处理和保存。

## 核心功能

- **企业微信消息同步**：使用官方 SDK 拉取消息存档，支持文本、图片、链接、视频、文件等消息类型
- **Telegram 消息同步**：支持 Telegram Bot 消息接收
- **邮件轮询**：自动检查新邮件
- **Craft 集成**：将消息智能转换为 Craft 原生块保存到文档
- **生日提醒**：支持农历/公历生日提醒
- **AI 新闻播报**：使用 CrewAI 自动生成新闻内容

## 技术栈

- **语言**：Python 3.12
- **框架**：FastAPI + uvicorn
- **部署**：Docker + Docker Compose
- **集成**：企业微信消息归档、Craft 笔记

## 项目结构

```
SaveHelper/
├── main.py                      # 主入口 (FastAPI + 调度器)
├── docker-deploy.sh             # Docker 部署脚本
├── docker/
│   ├── Dockerfile               # Docker 构建文件
│   └── docker-compose.yml       # Docker Compose 配置
├── backend/
│   ├── src/
│   │   ├── api/                 # API 路由
│   │   │   └── routers/         # 各模块路由
│   │   ├── services/            # 服务模块
│   │   │   ├── craft.py         # Craft 集成
│   │   │   ├── wecom.py         # 企业微信 SDK
│   │   │   ├── telegram.py      # Telegram 服务
│   │   │   ├── database.py      # 数据库服务
│   │   │   ├── cos.py           # 腾讯云 COS
│   │   │   └── ...
│   │   ├── handlers/            # 消息处理器
│   │   ├── crew_news/           # AI 新闻生成
│   │   ├── crew_lottery/        # 抽奖功能
│   │   ├── birthday_reminder/   # 生日提醒
│   │   ├── models/              # 数据模型
│   │   └── utils/               # 工具函数
│   └── sql/                     # 数据库初始化脚本
└── .env                         # 环境变量配置
```

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```ini
# 企业微信
WECOM_CORP_ID=your_corp_id
WECOM_APP_SECRET=your_app_secret
WECOM_TOKEN=your_token
WECOM_ENCODING_AES_KEY=your_aes_key

# Craft
CRAFT_API_TOKEN=your_craft_token
CRAFT_LINKS_ID=your_links_doc_id

# Telegram (可选)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_PROXY_URL=proxy_url

# 腾讯云 COS (可选)
COS_SECRET_ID=your_secret_id
COS_SECRET_KEY=your_secret_key
COS_REGION=ap-shanghai
COS_BUCKET=your_bucket

# 数据库
SQLITE_DB_PATH=data/savehelper.db
```

### 2. Docker 部署

```bash
# 一键部署（包含构建、启动、健康检查）
./docker-deploy.sh

# 查看日志
docker logs -f savehelper_app
```

### 3. 本地开发

```bash
# 安装依赖
pip install -r backend/requirements.txt

# 启动服务
python main.py
```

## API 端点

- `GET /` - 健康检查
- `GET /scalar` - API 文档
- `POST /craft/save` - 保存消息到 Craft
- `POST /birthday/add` - 添加生日提醒
- `GET /birthday/list` - 列出生日提醒
- `POST /lottery/draw` - 抽奖

## 验证与测试

修改代码后必须运行 `./docker-deploy.sh` 重新构建并验证：

```bash
./docker-deploy.sh

# 验证服务
curl http://localhost:8000/

# 检查日志
docker logs savehelper_app
```

## 环境变量说明

| 变量 | 说明 | 必需 |
|------|------|------|
| `WECOM_CORP_ID` | 企业ID | 是 |
| `WECOM_APP_SECRET` | 消息存档 Secret | 是 |
| `CRAFT_API_TOKEN` | Craft API Token | 是 |
| `CRAFT_LINKS_ID` | Craft 文档 ID | 是 |

## 许可证

MIT
