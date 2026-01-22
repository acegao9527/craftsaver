"""
用户绑定服务模块
处理企微用户与Craft文档的映射关系
"""
import json
import logging
import os
from typing import Optional, List
from datetime import datetime

import requests

from src.models.binding import UserBinding, BindingCreate, BindingResponse
from src.services.database import get_connection

logger = logging.getLogger(__name__)

# Craft 配置
CRAFT_API_TOKEN = os.getenv("CRAFT_API_TOKEN")
CRAFT_LINKS_ID = os.getenv("CRAFT_LINKS_ID")
API_BASE_URL = "https://connect.craft.do/links"

# 默认用户配置
DEFAULT_CRAFT_LINK_ID = os.getenv("DEFAULT_CRAFT_LINK_ID", "")
DEFAULT_CRAFT_DOCUMENT_ID = os.getenv("DEFAULT_CRAFT_DOCUMENT_ID", "")


class BindingService:
    """绑定服务类"""

    @staticmethod
    def create_binding(create: BindingCreate) -> Optional[UserBinding]:
        """创建或更新用户绑定"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                # 检查是否已存在
                cursor.execute(
                    "SELECT id FROM user_mappings WHERE wecom_openid = ?",
                    (create.wecom_openid,)
                )
                existing = cursor.fetchone()

                if existing:
                    # 更新
                    cursor.execute("""
                        UPDATE user_mappings
                        SET craft_link_id = ?, craft_document_id = ?, craft_token = ?, display_name = ?, updated_at = ?
                        WHERE wecom_openid = ?
                    """, (
                        create.craft_link_id,
                        create.craft_document_id,
                        create.craft_token,
                        create.display_name,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        create.wecom_openid
                    ))
                    binding_id = existing['id']
                else:
                    # 插入
                    cursor.execute("""
                        INSERT INTO user_mappings (wecom_openid, craft_link_id, craft_document_id, craft_token, display_name)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        create.wecom_openid,
                        create.craft_link_id,
                        create.craft_document_id,
                        create.craft_token,
                        create.display_name
                    ))
                    binding_id = cursor.lastrowid

                conn.commit()
                return BindingService.get_binding_by_openid(create.wecom_openid)

        except Exception as e:
            logger.error(f"[Binding] 创建绑定失败: openid={create.wecom_openid}, error={e}")
            return None

    @staticmethod
    def get_binding_by_openid(openid: str) -> Optional[UserBinding]:
        """根据企微OpenID获取绑定"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM user_mappings WHERE wecom_openid = ? AND is_enabled = 1",
                    (openid,)
                )
                row = cursor.fetchone()
                if row:
                    return BindingService._row_to_binding(row)
                return None
        except Exception as e:
            logger.error(f"[Binding] 查询绑定失败: openid={openid}, error={e}")
            return None

    @staticmethod
    def get_all_bindings() -> List[UserBinding]:
        """获取所有绑定"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_mappings ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [BindingService._row_to_binding(row) for row in rows]
        except Exception as e:
            logger.error(f"[Binding] 获取所有绑定失败: error={e}")
            return []

    @staticmethod
    def delete_binding(openid: str) -> bool:
        """删除绑定"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_mappings WHERE wecom_openid = ?", (openid,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[Binding] 删除绑定失败: openid={openid}, error={e}")
            return False

    @staticmethod
    def get_default_target() -> Optional[dict]:
        """获取默认用户的目标配置"""
        if DEFAULT_CRAFT_LINK_ID and DEFAULT_CRAFT_DOCUMENT_ID and DEFAULT_CRAFT_TOKEN:
            return {
                "link_id": DEFAULT_CRAFT_LINK_ID,
                "document_id": DEFAULT_CRAFT_DOCUMENT_ID,
                "token": DEFAULT_CRAFT_TOKEN
            }
        return None

    @staticmethod
    def _row_to_binding(row) -> UserBinding:
        """将数据库行转换为UserBinding对象"""
        return UserBinding(
            id=row['id'],
            wecom_openid=row['wecom_openid'],
            craft_link_id=row['craft_link_id'],
            craft_document_id=row['craft_document_id'],
            craft_token=row.get('craft_token'),
            display_name=row.get('display_name'),
            is_enabled=bool(row['is_enabled']) if 'is_enabled' in row else True,
            created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
            updated_at=datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
        )


def verify_craft_access(link_id: str, document_id: str, token: str = None) -> tuple[bool, str]:
    """
    验证Craft链接和文档ID是否可访问

    Args:
        link_id: Craft 链接 ID
        document_id: Craft 文档 ID
        token: 文档 Token（可选）

    Returns:
        (是否成功, 错误信息/显示名称)
    """
    effective_token = token or CRAFT_API_TOKEN
    if not effective_token:
        return False, "未配置 CRAFT_API_TOKEN"

    url = f"{API_BASE_URL}/{link_id}/api/v1/blocks"
    headers = {
        "Authorization": f"Bearer {effective_token}",
        "Content-Type": "application/json",
    }
    params = {
        "id": document_id,
        "maxDepth": -2,
        "fetchMetadata": "false"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 尝试获取文档标题
            title = None
            if isinstance(data, dict):
                title = data.get('title') or data.get('name') or data.get('content', {}).get('title')
            if title:
                return True, title
            return True, document_id
        else:
            return False, f"验证失败: HTTP {response.status_code}"
    except Exception as e:
        return False, f"验证失败: {str(e)}"
