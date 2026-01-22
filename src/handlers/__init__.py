from .forward import ForwardHandler

# 定义 Handler 链表 (按优先级排序)
HANDLERS = [
    ForwardHandler(),    # 企微消息自动转发到 Craft
]


def get_handlers():
    """获取所有 handler"""
    return HANDLERS