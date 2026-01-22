#!/usr/bin/env python3
"""测试 iMessage 发送功能"""
import sys
sys.path.insert(0, '/Users/acelee/workspace/SaveHelper/backend/imessage')

from client import iMessageClient
import sqlite3

# 获取最新收到的消息
conn = sqlite3.connect('/Users/acelee/Library/Messages/chat.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT ROWID, text, handle_id, is_from_me
    FROM message
    WHERE text IS NOT NULL AND text != '' AND is_from_me = 0
    ORDER BY date DESC
    LIMIT 1
""")
row = cursor.fetchone()
conn.close()

if row:
    client = iMessageClient()
    sender = client._parse_handle_id(row["handle_id"]) if row["handle_id"] else ""
    print(f"最新消息来自: {sender}")
    print(f"内容: {row['text'][:50]}...")

    if sender:
        print(f"发送回复到: {sender}")
        success = client.send_text(sender, "你好")
        print(f"发送结果: {'成功' if success else '失败'}")
else:
    print("没有收到新消息")
