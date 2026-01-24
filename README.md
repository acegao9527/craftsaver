# CraftSaver - 企业微信消息同步工具

## 项目简介

CraftSaver 是一个将企业微信消息同步到 Craft 文档的工具，支持多种消息类型（文本、图片、链接、文件等）的自动处理和保存。

## 核心功能

- **企业微信消息同步**：使用官方 SDK 拉取消息存档，支持文本、图片、链接、视频、文件等消息类型
- **统一消息存储**：将消息统一存储到 SQLite 数据库
- **Craft 集成**：将消息智能转换为 Craft 原生块保存到文档
- **用户绑定**：每个用户可绑定自己的 Craft 文档

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

# SQLite 数据库
SQLITE_DB_PATH=data/craftsaver.db

# 腾讯云 COS 配置（用于上传图片/文件到云存储）
# 从腾讯云控制台获取: https://console.cloud.tencent.com/cos
COS_SECRET_ID=your_cos_secret_id
COS_SECRET_KEY=your_cos_secret_key
COS_REGION=ap-shanghai
COS_BUCKET=wecom-1373472507
COS_BASE_URL=https://wecom-1373472507.cos.ap-shanghai.myqcloud.com
COS_ROOT_DIR=lhcos-data

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

### 3. 创建用户绑定

部署完成后，通过 API 创建用户绑定：

```bash
# 创建绑定（每个企微用户需要绑定自己的 Craft 文档）
curl -X POST http://localhost:8001/bindings \
  -H "Content-Type: application/json" \
  -d '{
    "wecom_openid": "用户OpenID",
    "craft_link_id": "Craft链接ID",
    "craft_document_id": "Craft文档ID",
    "craft_token": "pdk_xxx",
    "display_name": "显示名称"
  }'
```

## API 端点

### 健康检查
- `GET /` - 服务状态

### 绑定管理
- `GET /bindings` - 获取所有绑定
- `GET /bindings/{openid}` - 获取单个绑定
- `POST /bindings` - 创建/更新绑定
- `PUT /bindings/{openid}` - 更新绑定
- `DELETE /bindings/{openid}` - 删除绑定
- `POST /bindings/verify` - 验证 Craft 访问权限

### Craft（已移除全局配置）

## 消息转发流程

1. 企微消息到达
2. 根据 `from_user` 查询绑定
3. 找到绑定 → 发送到对应的 Craft 文档
4. 未找到绑定 → 打印日志并丢弃消息

## 验证与测试

修改代码后必须运行 `./docker-deploy.sh` 重新构建并验证：

```bash
./docker-deploy.sh

# 验证服务
curl http://localhost:8001/

# 检查日志
docker logs craftsaver_app

# 查看 API 文档
# 访问 http://localhost:8001/scalar
```

## 环境变量说明

| 变量 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `WECOM_CORP_ID` | 企业ID | 是 | - |
| `WECOM_APP_SECRET` | 消息存档 Secret | 是 | - |
| `WECOM_TOKEN` | 回调 Token | 是 | - |
| `WECOM_ENCODING_AES_KEY` | 回调 AES Key | 是 | - |
| `WECOM_BOT_USERID` | 机器人UserID（可选） | 否 | - |
| `COS_SECRET_ID` | 腾讯云 SecretId（用于上传图片） | 是 | - |
| `COS_SECRET_KEY` | 腾讯云 SecretKey | 是 | - |
| `COS_REGION` | 腾讯云存储桶地域 | 是 | ap-shanghai |
| `COS_BUCKET` | 腾讯云存储桶名称 | 是 | - |
| `COS_BASE_URL` | 腾讯云存储桶访问地址 | 是 | - |
| `COS_ROOT_DIR` | 腾讯云存储根目录 | 是 | lhcos-data |
| `APP_PORT` | 应用端口 | 否 | 8001 |
| `SQLITE_DB_PATH` | SQLite 数据库文件路径 | 否 | data/craftsaver.db |

**注意**：
- `CRAFT_API_TOKEN`、`CRAFT_LINKS_ID` 不再使用全局配置
- 每个用户的 Craft 配置通过绑定 API 存储在数据库中
- 未绑定的用户消息会被丢弃
- 图片/文件会自动上传到腾讯云 COS

## 许可证

MIT
