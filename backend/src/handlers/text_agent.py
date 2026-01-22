"""
TextAgentHandler - 纯文本智能处理
Priority: 4 (TestHandler 之后，ImageHandler 之前)

流程：
1. 规则初筛（长度、URL 过滤等）
2. Agent 判断（问答 vs 记录）
3. 问答 → 直接回复
4. 记录 → 保存 Craft
"""
import re
import logging
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage
from src.services.craft import save_blocks_to_craft
from src.services.formatter import format_unified_message_as_craft_blocks
# crew.py 的导入延迟到函数内部，避免在模块加载时初始化 CrewAI

logger = logging.getLogger(__name__)

# 规则配置
RULES = {
    "min_length": 2,           # 最小长度（避免单字符）
    "max_length": 500,         # 最大长度（太长不处理，降级到 DefaultHandler）
    "exclude_patterns": [      # 排除模式
        r"^新闻:",             # 新闻关键字
        r"^测试",              # 测试关键字
    ],
}


class TextAgentHandler(BaseHandler):
    """
    处理纯文本消息（不含链接）

    仅处理短文本（≤500字符），超出长度降级到 DefaultHandler
    """

    async def check(self, msg: UnifiedMessage) -> bool:
        """检查是否应该处理该消息"""
        # 1. 仅处理文本类型
        if msg.msg_type != "text":
            return False

        content = msg.content.strip()

        # 2. 长度检查（过长降级）
        if len(content) < RULES["min_length"]:
            return False
        if len(content) > RULES["max_length"]:
            return False

        # 3. 排除已定义关键字
        for pattern in RULES["exclude_patterns"]:
            if re.match(pattern, content):
                return False

        # 4. 排除 URL（由 LinkHandler 处理）
        if re.search(r'https?://', content):
            return False

        return True

    async def handle(self, msg: UnifiedMessage):
        """处理文本消息"""
        logger.info(f"[TextAgentHandler] Processing: {msg.msg_id}, content: {msg.content[:50]}...")

        try:
            # 1. 调用 Agent 判断（延迟导入避免启动时冲突）
            from src.agents.text_agent import run_text_classification
            result = run_text_classification(msg.content)
            logger.info(f"[TextAgentHandler] Agent result: {result}")

            # 2. 根据判断结果处理
            if result.get("answer") is True:
                # 问答类：直接回复
                reply_text = result.get("reply") or "我收到你的问题了~"
                await self.reply(msg, reply_text)
                logger.info(f"[TextAgentHandler] Answered question: {msg.msg_id}")

            else:
                # 记录类：保存 Craft
                await self._save_to_craft(msg, result)

        except Exception as e:
            logger.error(f"[TextAgentHandler] Error: {e}", exc_info=True)
            # 降级：保存到 Craft
            await self._fallback_save(msg)

    async def _save_to_craft(self, msg: UnifiedMessage, result: dict):
        """保存记录类消息到 Craft"""
        blocks = format_unified_message_as_craft_blocks(msg)

        if not blocks:
            logger.warning(f"[TextAgentHandler] Empty blocks: {msg.msg_id}")
            return

        success = await save_blocks_to_craft(blocks)

        if success:
            await self.reply(msg, "✅ 已保存到笔记")
            logger.info(f"[TextAgentHandler] Saved to Craft: {msg.msg_id}")
        else:
            await self.reply(msg, "⚠️ 保存失败，请重试")
            logger.error(f"[TextAgentHandler] Save failed: {msg.msg_id}")

    async def _fallback_save(self, msg: UnifiedMessage):
        """降级保存逻辑（异常时使用）"""
        try:
            blocks = format_unified_message_as_craft_blocks(msg)
            if blocks:
                success = await save_blocks_to_craft(blocks)
                if success:
                    await self.reply(msg, "✅ 消息已保存")
        except Exception as save_error:
            logger.error(f"[TextAgentHandler] Fallback save failed: {save_error}")
