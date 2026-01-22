import logging
import os
import requests
import json
import asyncio
from typing import Optional
from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)

async def _send_rpa_notification(text: str):
    """调用 RPA 发送企微通知"""
    url = os.getenv("RPA_NOTIFICATION_URL", "http://192.168.31.8:8000/send")
    headers = {"Content-Type": "application/json"}
    payload = {"text": text}
    
    logger.debug(f"[RPA] 请求详情: URL={url}, Payload={json.dumps(payload, ensure_ascii=False)}")

    try:
        response = await asyncio.to_thread(requests.post, url, json=payload, headers=headers, timeout=10)
        # response_text = response.text[:500] 
        # logger.info(f"[RPA] 收到响应: Status={response.status_code}, Body='{response_text}'")
        response.raise_for_status()
        logger.info(f"[RPA] 通知发送成功。")

    except requests.exceptions.RequestException as e:
        logger.error(f"[RPA] 通知发送失败: {e}")

async def send_reply(msg: UnifiedMessage, text: str):
    """
    统一回复工具函数
    """
    try:
        if msg.source == 'wecom':
            # 企微消息不再调用 RPA 回复，保持静默
            logger.info(f"[Reply] 企微消息静默处理，跳过 RPA 回复: msg_id={msg.msg_id}")
            return
        elif msg.source == 'telegram':
            # Telegram 回复
            chat_id = None
            if msg.raw_data and 'message' in msg.raw_data:
                chat_id = msg.raw_data['message'].get('chat', {}).get('id')

            if chat_id:
                # Lazy import
                from src.services.telegram import send_telegram_message
                await send_telegram_message(str(chat_id), text)
            else:
                logger.warning(f"[Reply] Cannot find chat_id for Telegram message: {msg.msg_id}")
        elif msg.source == 'email_notification':
            # 邮件通知，直接发送 RPA
            await _send_rpa_notification(text)
        else:
            logger.warning(f"[Reply] Unsupported source for reply: {msg.source}")
    except Exception as e:
        logger.error(f"[Reply] Failed to send reply: {e}", exc_info=True)
