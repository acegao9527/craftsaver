"""
Craft 集成服务模块
"""
import json
import logging
import os
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# Craft 配置
CRAFT_API_TOKEN = os.getenv("CRAFT_API_TOKEN")
CRAFT_LINKS_ID = os.getenv("CRAFT_LINKS_ID")
CRAFT_INBOX_PAGE_ID = os.getenv("CRAFT_INBOX_PAGE_ID")
API_BASE_URL = "https://connect.craft.do/links"


async def save_blocks_to_craft(
    blocks: List[Dict],
    link_id: str = None,
    document_id: str = None,
    document_token: str = None
):
    """
    保存 blocks 到 Craft

    Args:
        blocks: 要保存的 blocks 列表
        link_id: Craft 链接 ID（可选，默认使用全局配置）
        document_id: Craft 文档 ID（可选，默认使用全局配置）
        document_token: Craft 文档 Token（可选，用于访问私有文档）
    """
    # 使用传入的配置或全局配置
    effective_link_id = link_id or CRAFT_LINKS_ID
    effective_document_id = document_id or CRAFT_INBOX_PAGE_ID
    effective_token = document_token or CRAFT_API_TOKEN

    if not all([effective_token, effective_link_id]):
        logger.error("[Craft] Missing required configuration for Craft.")
        return False

    logger.info(f"[Craft] 开始保存: {len(blocks)} blocks -> link={effective_link_id}, doc={effective_document_id}")
    for i, block in enumerate(blocks):
        logger.info(f"[Craft] Block[{i}]: {block}")

    url = f"{API_BASE_URL}/{effective_link_id}/api/v1/blocks"
    headers = {
        "Authorization": f"Bearer {effective_token}",
        "Content-Type": "application/json",
    }
    body = {
        "blocks": blocks,
        "position": {
            "position": "end",
            "pageId": effective_document_id
        }
    }

    try:
        # 打印完整的 HTTP 请求信息
        logger.info(f"[Craft] === HTTP Request ===")
        logger.info(f"[Craft] POST {url}")
        logger.info(f"[Craft] Headers: {{'Authorization': 'Bearer {CRAFT_API_TOKEN[:20]}...', 'Content-Type': 'application/json'}}")
        logger.info(f"[Craft] Body: {body}")
        response = requests.request("POST", url, json=body, headers=headers)
        logger.info(f"[Craft] === HTTP Response ===")
        logger.info(f"[Craft] Status: {response.status_code}")
        logger.info(f"[Craft] Body: {response.text[:500] if response.text else 'empty'}")

        # 检查是否是弃用警告
        if "deprecated" in response.text.lower() or "single document" in response.text.lower():
            logger.error(f"[Craft] 保存失败: API 已弃用，请创建新的 Multi Document API")
            return False

        # 尝试解析 JSON 响应
        try:
            response_json = response.json()
            if response.status_code in (200, 201) and "items" in response_json:
                logger.info(f"[Craft] 保存成功: {len(blocks)} blocks")
                return True
            else:
                logger.error(f"[Craft] 保存失败: 响应格式异常 {response_json}")
                return False
        except json.JSONDecodeError:
            if response.status_code == 200:
                logger.info(f"[Craft] 保存成功（无 JSON 响应）: {len(blocks)} blocks")
                return True
            logger.error(f"[Craft] 保存失败: 响应不是有效 JSON")
            return False

    except Exception as e:
        logger.error(f"[Craft] 请求异常: {e}")
        return False

async def add_collection_item(collection_id: str, items: List[Dict]):
    """
    向 Craft Collection 添加项

    Args:
        collection_id: Collection ID
        items: 要添加的项列表，格式符合 Collection Schema
    """
    if not all([CRAFT_API_TOKEN, CRAFT_LINKS_ID]):
        logger.error("Error: Missing required environment variables for Craft.")
        return False

    url = f"{API_BASE_URL}/{CRAFT_LINKS_ID}/api/v1/collections/{collection_id}/items"
    headers = {
        "Authorization": f"Bearer {CRAFT_API_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {
        "items": items
    }

    try:
        logger.info(f"[Craft] Adding {len(items)} items to collection {collection_id}")
        logger.debug(f"[Craft] Collection Request Body: {json.dumps(body, ensure_ascii=False)}")
        
        response = requests.post(url, json=body, headers=headers)
        
        logger.info(f"[Craft] Collection Status: {response.status_code}")
        if response.status_code in (200, 201):
            logger.info(f"[Craft] Successfully added items to collection {collection_id}")
            return True
        else:
            logger.error(f"[Craft] Failed to add collection item: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[Craft] Collection Request exception: {e}")
        return False


def init_craft(api_token: str = None, links_id: str = None) -> None:
    """初始化 Craft 配置"""
    global CRAFT_API_TOKEN, CRAFT_LINKS_ID
    if api_token:
        CRAFT_API_TOKEN = api_token
    if links_id:
        CRAFT_LINKS_ID = links_id
    logger.info(f"[Craft] 初始化成功: links_id={CRAFT_LINKS_ID}")


def fetch_todo_doc_id() -> Optional[str]:
    """获取待办文档 ID"""
    return os.getenv("CRAFT_TODO_DOC_ID")


def fetch_todo_blocks() -> List[Dict]:
    """
    获取 Craft 待办文档中的所有 blocks

    使用 fetch API 获取指定文档的 blocks，递归收集所有层级的 blocks

    Returns:
        blocks 列表
    """
    doc_id = fetch_todo_doc_id()
    if not doc_id:
        logger.warning("[Craft] 未配置 CRAFT_TODO_DOC_ID")
        return []

    if not all([CRAFT_LINKS_ID, CRAFT_API_TOKEN]):
        logger.warning("[Craft] 未配置 Craft API")
        return []

    url = f"{API_BASE_URL}/{CRAFT_LINKS_ID}/api/v1/blocks"
    headers = {
        "Authorization": f"Bearer {CRAFT_API_TOKEN}"
    }
    params = {
        "id": doc_id,
        "maxDepth": -2,
        "fetchMetadata": "false"
    }

    try:
        logger.info("[Craft] 获取待办文档 blocks...")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        all_blocks = []
        if isinstance(data, dict):
            _collect_blocks_recursive(data, all_blocks)

        logger.info(f"[Craft] 共获取到 {len(all_blocks)} 个 blocks")
        return all_blocks

    except requests.exceptions.RequestException as e:
        logger.error(f"[Craft] 获取 blocks 失败: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"[Craft] 解析响应失败: {e}")
        return []


def _collect_blocks_recursive(block: Dict, results: List[Dict]) -> None:
    """
    递归收集所有 blocks（排除根 page block）

    Args:
        block: 当前 block
        results: 结果列表
    """
    if not isinstance(block, dict):
        return

    block_type = block.get("type", "")
    if block_type != "page":
        results.append(block)

    children = block.get("content", [])
    if isinstance(children, list):
        for child in children:
            _collect_blocks_recursive(child, results)


def filter_today_todos(blocks: List[Dict], today: str) -> List[Dict]:
    """
    筛选当天的未完成待办任务

    条件：
    - listStyle 为 "task"
    - taskInfo 中包含当天日期
    - 任务状态为未完成（state 为 todo）

    Args:
        blocks: 所有 blocks
        today: 当天日期字符串

    Returns:
        符合条件的待办列表
    """
    today_todos = []

    for block in blocks:
        if not isinstance(block, dict):
            continue

        # 检查 listStyle
        if block.get("listStyle") != "task":
            continue

        # 获取 taskInfo
        task_info = block.get("taskInfo", {})
        if not task_info:
            continue

        # 检查日期和状态
        if task_info.get("scheduleDate") != today:
            continue
        if task_info.get("state") != "todo":
            continue

        content = block.get("markdown", "")
        if content:
            today_todos.append({
                "doc_name": "Craft 待办",
                "text": content.strip(),
                "schedule_date": today,
                "block_id": block.get("id", "")
            })

    logger.info(f"[Craft] 筛选出 {len(today_todos)} 个当天未完成待办")
    return today_todos
