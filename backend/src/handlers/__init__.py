from .link import LinkHandler
from .news import NewsHandler
from .test import TestHandler
from .lottery import LotteryHandler
from .quote import QuoteHandler
from .bind import BindHandler
from .forward import ForwardHandler
# TextAgentHandler 延迟导入，避免在模块加载时初始化 CrewAI 导致与 WeCom SDK 冲突
# from .text_agent import TextAgentHandler
from .media import ImageHandler
from .text import DefaultHandler

# 定义 Handler 链表 (按优先级排序)
HANDLERS = [
    BindHandler(),       # 0. 绑定命令（最高优先级）
    ForwardHandler(),    # 1. 消息转发（企微消息自动转发到 Craft）
    LinkHandler(),       # 2. 链接
    LotteryHandler(),    # 3. 抽奖 (New)
    QuoteHandler(),      # 4. 台词
    NewsHandler(),       # 5. 新闻关键字
    TestHandler(),       # 6. 测试关键字
    # TextAgentHandler(),  # 7. 纯文本 Agent（延迟导入，待解决 CrewAI 冲突后启用）
    ImageHandler(),      # 8. 图片
    DefaultHandler()     # 9. 兜底
]


def get_handlers():
    """动态获取所有 handler（包括延迟导入的）"""
    from .text_agent import TextAgentHandler
    handlers = HANDLERS.copy()
    # 插入 TextAgentHandler 到正确位置 (After TestHandler)
    handlers.insert(4, TextAgentHandler())
    return handlers