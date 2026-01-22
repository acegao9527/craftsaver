"""
SaveHelper - 企业微信到 Craft 消息同步工具

主入口
"""
import logging
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from src.utils.logger import setup_logging

# 加载环境变量 (必须在日志配置前加载，以便读取 LOG_LEVEL_*)
load_dotenv()

# 配置日志 (使用模块化配置)
setup_logging()
startup_logger = logging.getLogger("savehelper.startup")

# WeCom 配置
WECOM_TOKEN = os.getenv("WECOM_TOKEN")
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID")
WECOM_ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY")
WECOM_APP_SECRET = os.getenv("WECOM_APP_SECRET")
WECOM_PRIVATE_KEY_PATH = os.getenv("WECOM_PRIVATE_KEY_PATH", "private_key.pem")

# 1. 初始化 WeCom SDK (必须最先初始化，以避免与其他库的 C 扩展冲突)
try:
    from src.services.wecom import init_wecom
    init_wecom(
        corp_id=WECOM_CORP_ID,
        chat_secret=WECOM_APP_SECRET,
        private_key_path=WECOM_PRIVATE_KEY_PATH
    )
    startup_logger.info("WeCom SDK Initialized successfully.")
except Exception as e:
    startup_logger.error(f"WeCom SDK initialization failed: {e}")

# 2. 初始化数据库
from src.services.database import init_db
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/savehelper.db")
init_db(db_path=SQLITE_DB_PATH)
startup_logger.info(f"Database config initialized (Path: {SQLITE_DB_PATH})")

# Craft 配置
CRAFT_API_TOKEN = os.getenv("CRAFT_API_TOKEN")
CRAFT_LINKS_ID = os.getenv("CRAFT_LINKS_ID")
CRAFT_DOC_ID = os.getenv("CRAFT_DOC_ID", "0")

# 3. 初始化 Craft
from src.services.craft import init_craft
init_craft(
    api_token=CRAFT_API_TOKEN,
    links_id=CRAFT_LINKS_ID
)
startup_logger.info("Craft Service initialized.")

# 4. 导入服务
import asyncio
from src.services.telegram import run_telegram_polling, get_last_offset
from src.services.wecom import run_wecom_polling, get_last_seq_from_file
from src.services.email_polling import run_email_polling
from src.services.scheduler import start_scheduler, shutdown_scheduler

# 5. 定义 lifespan 函数（替代 deprecated 的 on_event）
@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()


async def startup_event():
    """启动时运行后台任务"""
    # 0. 初始化数据库 (SQLite)
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        # Determine SQL directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sql_dir = os.path.join(base_dir, "sql")
        if not os.path.exists(sql_dir):
            sql_dir = os.path.join(base_dir, "backend", "sql")

        sql_files = [
            os.path.join(sql_dir, "create_unified_messages.sql"),
            os.path.join(sql_dir, "create_birthday_table.sql"),
            os.path.join(sql_dir, "create_emails.sql"),
            os.path.join(sql_dir, "create_lottery_table.sql"),
            os.path.join(sql_dir, "create_user_mappings.sql")
        ]

        for sql_file in sql_files:
            if os.path.exists(sql_file):
                with open(sql_file, "r") as f:
                    sql_script = f.read()
                    cursor.executescript(sql_script)
                    startup_logger.info(f"Executed SQL: {sql_file}")
            else:
                startup_logger.warning(f"SQL file not found: {sql_file}")

        conn.commit()
        cursor.close()
        conn.close()
        startup_logger.info("Database tables initialized.")
    except Exception as e:
        startup_logger.error(f"Failed to init database: {e}")

    # 显示当前偏移量状态
    try:
        tg_offset = get_last_offset()
        wecom_seq = get_last_seq_from_file()
        startup_logger.info(f"Current Offsets -> Telegram: {tg_offset}, WeCom: {wecom_seq}")
    except Exception as e:
        startup_logger.warning(f"Failed to read offsets: {e}")

    # 1. 启动 Telegram 轮询
    asyncio.create_task(run_telegram_polling())
    # 2. 启动 WeCom 轮询
    asyncio.create_task(run_wecom_polling())
    # 3. 启动邮件轮询
    asyncio.create_task(run_email_polling())
    # 4. 启动定时任务调度器
    start_scheduler()


async def shutdown_event():
    """关闭时清理资源"""
    shutdown_scheduler()


# 6. 创建 FastAPI 应用（使用 lifespan）
from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SaveHelper - WeCom to Craft Connector",
    description="企业微信消息存档同步到 Craft 文档",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 7. 注册路由 (最后导入，因为 routers 可能会导入 heavy libraries like crewai)
from src.api.routers import craft_router, news_router, telegram_router, lottery_router
from src.api.routers.admin import admin_router

app.include_router(craft_router)
app.include_router(news_router)
app.include_router(telegram_router)
app.include_router(lottery_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "SaveHelper is running", "version": "1.0.0"}


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    """Scalar API 文档"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
