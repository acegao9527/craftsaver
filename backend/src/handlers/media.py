import logging
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage
from src.services.craft import save_blocks_to_craft

logger = logging.getLogger(__name__)


def local_path_to_cos_url(local_path: str) -> str:
    """将本地路径转换为 COS URL"""
    filename = local_path.split("/")[-1]
    return f"https://wecom-1373472507.cos.ap-shanghai.myqcloud.com/lhcos-data/{filename}"


class ImageHandler(BaseHandler):
    """
    处理图片类消息
    Priority: 4
    """
    async def check(self, msg: UnifiedMessage) -> bool:
        return msg.msg_type == "image"

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[ImageHandler] Processing image message: {msg.msg_id}")

        # 获取 COS URL（将本地路径转换为 COS URL）
        cos_url = local_path_to_cos_url(msg.content)

        # 构建 image block
        blocks = [{
            "type": "image",
            "url": cos_url
        }]

        # 保存到 Craft
        success = await save_blocks_to_craft(blocks)

        # 回复
        if success:
            await self.reply(msg, "已收到图片，保存到收件箱，期待你的查看")
        else:
            await self.reply(msg, "⚠️ 图片保存失败")
