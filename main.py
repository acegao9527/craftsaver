"""
craftSaver - 企业微信到 Craft 消息同步工具

主入口：仅处理企微消息转存到 Craft
"""
import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from src.utils.logger import setup_logging

# 加载环境变量
load_dotenv()

# 配置日志
setup_logging()
startup_logger = logging.getLogger("craftsaver.startup")

# WeCom 配置
WECOM_TOKEN = os.getenv("WECOM_TOKEN")
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID")
WECOM_ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY")
WECOM_APP_SECRET = os.getenv("WECOM_APP_SECRET")
WECOM_PRIVATE_KEY_PATH = os.getenv("WECOM_PRIVATE_KEY_PATH", "private_key.pem")

# 1. 初始化 WeCom SDK
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
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/craftsaver.db")
init_db(db_path=SQLITE_DB_PATH)
startup_logger.info(f"Database config initialized (Path: {SQLITE_DB_PATH})")

# Craft 配置
CRAFT_API_TOKEN = os.getenv("CRAFT_API_TOKEN")
CRAFT_LINKS_ID = os.getenv("CRAFT_LINKS_ID")

# 应用配置
APP_PORT = int(os.getenv("APP_PORT", "8002"))
APP_TITLE = "craftSaver - WeCom to Craft Connector"

# 3. 初始化 Craft
from src.services.craft import init_craft
init_craft(
    api_token=CRAFT_API_TOKEN,
    links_id=CRAFT_LINKS_ID
)
startup_logger.info("Craft Service initialized.")

# 4. 导入服务
import asyncio
from src.services.wecom import run_wecom_polling

# 5. 定义 lifespan 函数
@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    await startup_event()
    yield
    await shutdown_event()


async def startup_event():
    """启动时运行后台任务"""
    # 初始化数据库表
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        base_dir = os.path.dirname(os.path.abspath(__file__))
        sql_dir = os.path.join(base_dir, "src/sql")

        sql_files = [
            os.path.join(sql_dir, "create_unified_messages.sql"),
            os.path.join(sql_dir, "create_user_mappings.sql")
        ]

        for sql_file in sql_files:
            if os.path.exists(sql_file):
                with open(sql_file, "r") as f:
                    sql_script = f.read()
                    cursor.executescript(sql_script)
                    startup_logger.info(f"Executed SQL: {sql_file}")

        conn.commit()
        cursor.close()
        conn.close()
        startup_logger.info("Database tables initialized.")
    except Exception as e:
        startup_logger.error(f"Failed to init database: {e}")

    # 启动 WeCom 轮询
    asyncio.create_task(run_wecom_polling())

    # 打印访问地址
    startup_logger.info(f"API 文档: http://localhost:{APP_PORT}/scalar")
    startup_logger.info(f"OpenAPI JSON: http://localhost:{APP_PORT}/openapi.json")


async def shutdown_event():
    """关闭时清理资源"""
    pass


# 6. 创建 FastAPI 应用
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="craftSaver - WeCom to Craft Connector",
    description="企业微信消息存档同步到 Craft 文档",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


@app.get("/scalar", include_in_schema=False)
async def scalar_docs(request: Request):
    return get_scalar_api_reference(
        openapi_url=str(request.url_for("openapi")),
        title=APP_TITLE,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 7. 注册路由
from src.api.routers import wecom_router, craft_router, binding_router

app.include_router(wecom_router)
app.include_router(craft_router)
app.include_router(binding_router)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "craftSaver is running", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=True)
