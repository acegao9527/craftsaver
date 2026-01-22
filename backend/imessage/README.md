# iMessage Module

macOS iMessage 收发模块。

## 使用方法

```python
from backend.imessage import iMessageClient, api

# 使用全局 API（推荐）
api.init()
api.send("+1234567890", "Hello from iMessage!")
api.send_attachment("+1234567890", "/path/to/image.jpg")

# 或使用客户端类
client = iMessageClient()
client.send_text("+1234567890", "Hello!")
client.send_attachment("+1234567890", "/path/to/file.pdf")

# 获取消息
messages = client.get_messages(limit=50)
for msg in messages:
    print(f"{msg.sender}: {msg.text}")


# 监控新消息
def on_new_message(msg):
    print(f"收到来自 {msg.sender} 的消息: {msg.text}")
    if msg.direction == "incoming":
        client.send_text(msg.sender, "已收到！")


client.start_watching(on_new_message)

# 停止监控
client.stop_watching()
client.close()
```

## 功能

- 发送文本消息
- 发送图片/文件附件
- 获取消息历史
- 实时监控新消息
- 自动回复

## 权限要求

需要在 macOS "系统设置" > "隐私与安全性" > "完全磁盘访问" 中授予权限。
