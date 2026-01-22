import logging
import httpx
import asyncio
import random
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)

# 影视台词库（备用，当外部 API 不可用时）
MOVIE_QUOTES = [
    {"quote": "人生就像一盒巧克力，你永远不知道下一颗是什么味道。", "movie": "《阿甘正传》"},
    {"quote": "希望是美好的，也许是人间至善，而美好的事物永不消逝。", "movie": "《肖申克的救赎》"},
    {"quote": "如果你有梦想的话，就要去捍卫它。", "movie": "《当幸福来敲门》"},
    {"quote": "永远不要轻易评判他人，因为你永远不知道他经历了什么。", "movie": "《奇迹男孩》"},
    {"quote": "死亡不是真正的逝去，遗忘才是。", "movie": "《寻梦环游记》"},
    {"quote": "生活就像一盒水果糖，你永远不知道下一颗是什么味道。", "movie": "《重庆森林》"},
    {"quote": "有些事情错过了就是一辈子。", "movie": "《大话西游》"},
    {"quote": "能力越大，责任越大。", "movie": "《蜘蛛侠》"},
    {"quote": "我想要怒放的生命。", "movie": "《飞屋环游记》"},
    {"quote": "不要忘记你的初心。", "movie": "《千与千寻》"},
    {"quote": "曾经有一份真挚的爱情摆在我面前，我没有珍惜。", "movie": "《大话西游》"},
    {"quote": "做人如果没有梦想，跟咸鱼有什么分别？", "movie": "《少林足球》"},
    {"quote": "星星之火，可以燎原。", "movie": "《盗梦空间》"},
    {"quote": "我命由我不由天。", "movie": "《哪吒之魔童降世》"},
    {"quote": "我们笑着说再见，却深知再见遥遥无期。", "movie": "《海上钢琴师》"},
    {"quote": "世界上只有一种病，就是穷病。", "movie": "《我不是药神》"},
    {"quote": "有些鸟是关不住的，因为它们的羽毛太鲜亮了。", "movie": "《肖申克的救赎》"},
    {"quote": "懦怯囚禁人的灵魂，希望可以让你自由。", "movie": "《肖申克的救赎》"},
    {"quote": "我猜中了开头，却猜不中这结局。", "movie": "《大话西游》"},
    {"quote": "真正的死亡是世界上再没有一个人记得你。", "movie": "《寻梦环游记》"},
    {"quote": "人生不能像做菜，把所有的料都准备好了才下锅。", "movie": "《饮食男女》"},
    {"quote": "念念不忘，必有回响。", "movie": "《一代宗师》"},
    {"quote": "只要心是诚的，上帝自然会保佑你。", "movie": "《触不可及》"},
    {"quote": "人潮人海中，又看到你。", "movie": "《甜蜜蜜》"},
    {"quote": "每个人都在等一个人，等一个能看到自己不同的人。", "movie": "《等一个人咖啡》"},
]

# 外部台词 API
EXTERNAL_QUOTE_API = "https://api.quotable.io/random?tags=movies"


class QuoteHandler(BaseHandler):
    """
    处理"台词"关键字，随机获取影视经典台词
    Priority: High (before News)
    """

    async def check(self, msg: UnifiedMessage) -> bool:
        if msg.msg_type == "text" and msg.content:
            return msg.content.strip() == "台词"
        return False

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[QuoteHandler] Processing quote request: {msg.msg_id}")

        try:
            # 优先使用外部 API
            quote_data = await self._fetch_quote_from_api()
            if quote_data:
                reply_text = f"💬 {quote_data['quote']}\n\n— {quote_data['movie']}"
                await self.reply(msg, reply_text)
            else:
                # 使用内置台词库
                random_quote = random.choice(MOVIE_QUOTES)
                reply_text = f"💬 {random_quote['quote']}\n\n— {random_quote['movie']}"
                await self.reply(msg, reply_text)

        except Exception as e:
            logger.error(f"[QuoteHandler] Error: {e}", exc_info=True)
            # 出错时使用内置台词库
            random_quote = random.choice(MOVIE_QUOTES)
            reply_text = f"💬 {random_quote['quote']}\n\n— {random_quote['movie']}"
            await self.reply(msg, reply_text)

    async def _fetch_quote_from_api(self):
        """从外部 API 获取随机影视台词"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(EXTERNAL_QUOTE_API)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("content") and data.get("author"):
                        return {
                            "quote": data["content"],
                            "movie": f"《{data['author']}》"
                        }
        except Exception as e:
            logger.warning(f"[QuoteHandler] External API failed: {e}")

        return None
