"""
邮件数据模型
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EmailAccount(BaseModel):
    """邮箱账号配置"""
    id: Optional[int] = None
    account: str                      # 邮箱账号
    imap_server: str                  # IMAP 服务器
    imap_port: int                    # IMAP 端口
    authorization_code: str           # 授权码
    folder: str = "INBOX"             # 邮件文件夹
    is_active: bool = True            # 是否启用
    last_uid: int = 0                 # 最后处理的 UID
    last_uid_time: int = 0            # 最后处理的时间戳


class Email(BaseModel):
    """邮件数据模型"""
    email_account: str                # 所属邮箱账号
    uid: str                          # IMAP UID
    subject: str = ""                 # 邮件主题
    sender: str = ""                  # 发件人邮箱
    sender_name: str = ""             # 发件人名称
    received_at: int                  # 收件时间戳
    preview: str = ""                 # 200字正文预览
    summary: Optional[str] = None     # LLM 生成的摘要
    importance: str = "medium"        # 重要性: high/medium/low
    action_items: list = []           # 待办事项
    raw_content: str = ""             # 原始邮件内容（JSON）
    created_at: int = 0               # 入库时间戳


class EmailSummary(BaseModel):
    """邮件摘要结果"""
    summary: str                      # 摘要
    importance: str = "medium"        # 重要性
    action_items: list = []           # 待办事项
