"""
消息格式化服务模块

将企微消息格式化为 Craft blocks
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)


class MessageFormatter:
    """消息格式化服务"""

    def __init__(self):
        pass

    def format_unified(self, msg: UnifiedMessage) -> List[Dict[str, Any]]:
        """
        格式化 UnifiedMessage 为 Craft blocks
        """
        blocks = []
        
        # 内容处理
        if msg.msg_type == "text":
            blocks.append({
                "type": "text",
                "markdown": msg.content
            })
        elif msg.msg_type == "image":
            # 图片处理: content 可能是本地路径或 COS URL
            if msg.content:
                # 检查是否是有效的 URL（以 http:// 或 https:// 开头）
                if msg.content.startswith("http://") or msg.content.startswith("https://"):
                    blocks.append({
                        "type": "image",
                        "url": msg.content
                    })
                # 检查本地文件是否存在
                elif os.path.exists(msg.content):
                    filename = os.path.basename(msg.content)
                    public_url = f"https://wecom-1373472507.cos.ap-shanghai.myqcloud.com/lhcos-data/{filename}"
                    blocks.append({
                        "type": "image",
                        "url": public_url
                    })
                else:
                    blocks.append({
                        "type": "text",
                        "markdown": f"🖼 **收到图片** (路径无效): `{msg.content}`"
                    })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": "🖼 **收到图片** (无内容)"
                })
        elif msg.msg_type == "file":
             # 文件处理: content 可能是本地路径或 COS URL
            if msg.content:
                # 优先从原始数据中获取真实文件名
                raw_file_data = msg.raw_data.get("file", {}) if msg.raw_data else {}
                display_name = raw_file_data.get("filename")

                # 检查是否是有效的 URL
                if msg.content.startswith("http://") or msg.content.startswith("https://"):
                    # 如果没有原始文件名，从 URL 中提取
                    if not display_name:
                        display_name = msg.content.split("/")[-1]
                    blocks.append({
                        "type": "file",
                        "url": msg.content,
                        "fileName": display_name,
                        "markdown": f"[{display_name}]({msg.content})"
                    })
                # 检查本地文件是否存在
                elif os.path.exists(msg.content):
                    # 如果没有原始文件名，则使用保存的文件名
                    if not display_name:
                        display_name = os.path.basename(msg.content)
                    saved_filename = os.path.basename(msg.content)
                    public_url = f"https://wecom-1373472507.cos.ap-shanghai.myqcloud.com/lhcos-data/{saved_filename}"
                    blocks.append({
                        "type": "file",
                        "url": public_url,
                        "fileName": display_name,
                        "markdown": f"[{display_name}]({public_url})"
                    })
                else:
                    blocks.append({
                        "type": "text",
                        "markdown": f"📁 **收到文件** (路径无效): `{msg.content}`"
                    })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": "📁 **收到文件** (无内容)"
                })
        elif msg.msg_type == "video":
            # 视频处理: content 可能是本地路径或 COS URL
            if msg.content:
                # 检查是否是有效的 URL
                if msg.content.startswith("http://") or msg.content.startswith("https://"):
                    filename = msg.content.split("/")[-1]
                    blocks.append({
                        "type": "file",
                        "url": msg.content,
                        "fileName": filename,
                        "markdown": f"[{filename}]({msg.content})"
                    })
                # 检查本地文件是否存在
                elif os.path.exists(msg.content):
                    import urllib.parse
                    filename = os.path.basename(msg.content)
                    safe_filename = urllib.parse.quote(filename)
                    public_url = f"https://wecom-1373472507.cos.ap-shanghai.myqcloud.com/lhcos-data/{safe_filename}"
                    blocks.append({
                        "type": "file",
                        "url": public_url,
                        "fileName": filename,
                        "markdown": f"[{filename}]({public_url})"
                    })
                else:
                    blocks.append({
                        "type": "text",
                        "markdown": f"🎥 **收到视频** (路径无效): `{msg.content}`"
                    })
            else:
                blocks.append({
                    "type": "text",
                    "markdown": "🎥 **收到视频** (无内容)"
                })
        elif msg.msg_type == "link":
             final_url = msg.content.strip()
             
             if final_url and final_url.startswith("http"):
                 blocks.append({
                    "type": "richUrl",
                    "url": final_url
                })
             else:
                 blocks.append({
                    "type": "text",
                    "markdown": f"🔗 **无效链接**: {final_url}"
                })
        else:
            blocks.append({
                "type": "text",
                "markdown": f"[{msg.msg_type}] {msg.content}"
            })
            
        return blocks

# 全局格式化器实例
_formatter = None


def get_formatter() -> MessageFormatter:
    """获取消息格式化器实例"""
    global _formatter
    if _formatter is None:
        _formatter = MessageFormatter()
    return _formatter


def format_unified_message_as_craft_blocks(msg: UnifiedMessage) -> List[Dict[str, Any]]:
    """将 UnifiedMessage 格式化为 Craft blocks"""
    return get_formatter().format_unified(msg)
