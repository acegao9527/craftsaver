"""
绑定处理器 - 处理用户绑定企微与Craft的命令
"""
import re
import logging
from src.models.chat_record import UnifiedMessage
from src.handlers.base import BaseHandler
from src.services.binding_service import BindingService, verify_craft_access
from src.models.binding import BindingCreate
from src.utils.reply_sender import send_reply

logger = logging.getLogger(__name__)


class BindHandler(BaseHandler):
    """绑定命令处理器"""

    # 命令模式: 绑定 linkId documentId token [显示名称]
    BIND_PATTERN = re.compile(r'^绑定\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)(?:\s+(.+))?$')
    MY_BIND_PATTERN = re.compile(r'^我的绑定$')

    async def check(self, msg: UnifiedMessage) -> bool:
        """检查是否是绑定相关命令"""
        if msg.msg_type != 'text':
            return False

        content = msg.content.strip()
        return bool(self.BIND_PATTERN.match(content) or self.MY_BIND_PATTERN.match(content))

    async def handle(self, msg: UnifiedMessage):
        """处理绑定命令"""
        content = msg.content.strip()

        # 我的绑定
        if self.MY_BIND_PATTERN.match(content):
            await self._handle_my_bind(msg)
            return

        # 绑定命令
        match = self.BIND_PATTERN.match(content)
        if match:
            link_id = match.group(1)
            document_id = match.group(2)
            token = match.group(3)
            display_name = match.group(4)

            await self._handle_bind(msg, link_id, document_id, token, display_name)

    async def _handle_bind(self, msg: UnifiedMessage, link_id: str, document_id: str, token: str, display_name: str = None):
        """处理绑定请求"""
        from_user = msg.from_user

        logger.info(f"[Bind] 收到绑定请求: from={from_user}, link={link_id}, doc={document_id}, token=***")

        # 验证 Craft 访问权限
        success, result = verify_craft_access(link_id, document_id, token)
        if not success:
            await send_reply(msg, f"绑定失败：{result}")
            return

        # 如果没有提供显示名称，使用验证返回的名称
        if not display_name:
            display_name = result

        # 创建绑定
        binding = BindingService.create_binding(BindingCreate(
            wecom_openid=from_user,
            craft_link_id=link_id,
            craft_document_id=document_id,
            craft_token=token,
            display_name=display_name
        ))

        if binding:
            # 发送成功通知到 Craft
            await self._send_bind_success_to_craft(binding)

            await send_reply(msg, f"绑定成功！\n\n"
                                  f"📋 文档：{display_name}\n"
                                  f"🔗 Link ID：{link_id}\n"
                                  f"📄 Document ID：{document_id}")
        else:
            await send_reply(msg, "绑定失败：保存绑定信息失败")

    async def _handle_my_bind(self, msg: UnifiedMessage):
        """查询当前用户的绑定信息"""
        from_user = msg.from_user

        binding = BindingService.get_binding_by_openid(from_user)
        if binding:
            await send_reply(msg, f"当前绑定：\n\n"
                                  f"📋 文档：{binding.display_name or '未命名'}\n"
                                  f"🔗 Link ID：{binding.craft_link_id}\n"
                                  f"📄 Document ID：{binding.craft_document_id}")
        else:
            await send_reply(msg, "当前未绑定 Craft 文档。\n\n"
                                  "请发送「绑定 linkId documentId token」进行绑定。\n\n"
                                  "示例：绑定 abc123 xyz456 pdk_xxx")

    async def _send_bind_success_to_craft(self, binding):
        """发送绑定成功通知到 Craft 文档"""
        from src.services.craft import save_blocks_to_craft
        from datetime import datetime

        blocks = [{
            "type": "paragraph",
            "content": [{
                "type": "text",
                "text": f"✅ 绑定成功 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }]
        }]

        try:
            await save_blocks_to_craft(
                blocks,
                link_id=binding.craft_link_id,
                document_id=binding.craft_document_id,
                document_token=binding.craft_token
            )
            logger.info(f"[Bind] 绑定成功通知已发送到 Craft")
        except Exception as e:
            logger.error(f"[Bind] 发送绑定通知失败: {e}")
