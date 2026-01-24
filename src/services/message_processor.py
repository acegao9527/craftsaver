import logging
from src.models.chat_record import UnifiedMessage
from src.services.database import DatabaseService
from src.handlers import get_handlers

logger = logging.getLogger(__name__)

# RPA related functions moved to src/utils/reply_sender.py
# News logic moved to src/handlers/news.py
# Link/Image/Text logic moved to respective handlers

async def _send_rpa_notification(text: str):
    """
    Deprecated: Use src.utils.reply_sender.send_reply instead.
    Kept temporarily if imported elsewhere, but internal logic delegates to new system.
    """
    from src.utils.reply_sender import _send_rpa_notification as new_rpa
    await new_rpa(text)

async def process_message(msg: UnifiedMessage):
    """
    核心消息处理分发器 (Dispatcher)

    流程：
    1. 落库 (Unified Storage) - 所有消息必须存档
    2. 分发给对应的 Handler 进行业务处理 (回复、同步Craft等)
    """
    # 1. 全局落库 (Audit Log)
    try:
        DatabaseService.save_unified_message(msg)
    except Exception as e:
        logger.error(f"[Dispatcher] DB Save failed: {e}")

    # 2. 查找并执行 Handler
    handled = False
    for handler in get_handlers():
        try:
            if await handler.check(msg):
                await handler.handle(msg)
                handled = True
                break
        except Exception as e:
            logger.error(f"[Dispatcher] Error in {handler.__class__.__name__}: {e}", exc_info=True)
            break

    if not handled:
        logger.warning(f"[Dispatcher] 消息未匹配处理器: msgid={msg.msg_id}, from_user={msg.from_user}")
