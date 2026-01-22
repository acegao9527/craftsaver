"""
系统配置 API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
import json
import logging

logger = logging.getLogger(__name__)
config_router = APIRouter(prefix="/config", tags=["Config"])

from src.api.deps import verify_token


# 配置文件路径
CONFIG_FILE = "data/admin_config.json"


def load_config() -> dict:
    """加载配置"""
    import os
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(data: dict):
    """保存配置"""
    import os
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@config_router.get("/list")
async def list_configs(token_info: dict = Depends(verify_token)):
    """获取自定义配置列表"""
    try:
        config = load_config()
        data = []
        for key, value in config.items():
            if key.endswith('_REMARK'):
                continue
            remark = config.get(f"{key}_REMARK", "")
            data.append({
                "config_key": key,
                "config_value": str(value),
                "remark": remark
            })

        return {"code": 200, "data": data}
    except Exception as e:
        logger.error(f"[Admin] 获取配置列表失败: {e}")
        return {"code": 200, "data": []}


@config_router.get("/{key}")
async def get_config(key: str, token_info: dict = Depends(verify_token)):
    """获取单个配置"""
    try:
        config = load_config()
        value = config.get(key)
        return {"code": 200, "data": value}
    except Exception as e:
        logger.error(f"[Admin] 获取配置失败: {e}")
        return {"code": 200, "data": None}


@config_router.get("")
async def get_all_configs(token_info: dict = Depends(verify_token)):
    """获取所有分组配置"""
    try:
        import os

        # 系统配置
        system_config = {
            "SYSTEM_NAME": os.getenv("SYSTEM_NAME", "SaveHelper"),
            "TIMEZONE": os.getenv("TIMEZONE", "Asia/Shanghai"),
            "MAINTENANCE_MODE": os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
        }

        # 从文件读取自定义配置
        file_config = load_config()

        return {"code": 200, "data": {**system_config, **file_config}}
    except Exception as e:
        logger.error(f"[Admin] 获取全部配置失败: {e}")
        return {"code": 200, "data": {}}


@config_router.put("/{key}")
async def set_config(key: str, body: dict, token_info: dict = Depends(verify_token)):
    """设置配置"""
    try:
        value = body.get("value")
        if value is None:
            raise HTTPException(status_code=400, detail="缺少 value 字段")

        config = load_config()
        config[key] = value
        save_config(config)

        logger.info(f"[Admin] 设置配置: {key}")
        return {"code": 200, "message": "设置成功"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"[Admin] 设置配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@config_router.delete("/{key}")
async def delete_config(key: str, token_info: dict = Depends(verify_token)):
    """删除配置"""
    try:
        config = load_config()
        if key in config:
            del config[key]
        # 同时删除备注
        remark_key = f"{key}_REMARK"
        if remark_key in config:
            del config[remark_key]
        save_config(config)

        logger.info(f"[Admin] 删除配置: {key}")
        return {"code": 200, "message": "删除成功"}
    except Exception as e:
        logger.error(f"[Admin] 删除配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
