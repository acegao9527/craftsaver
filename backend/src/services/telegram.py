import os
import logging
import time
import asyncio
import requests
import json
from typing import Optional, List, Dict, Any
from src.models.chat_record import UnifiedMessage

logger = logging.getLogger(__name__)
poll_logger = logging.getLogger("src.services.telegram.polling")  # 轮询专用 logger

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IMAGE_SAVE_DIR = os.getenv("IMAGE_SAVE_DIR", "/opt/lhcos-data")
OFFSET_FILE = "/app/data/.telegram_offset"
TELEGRAM_OFFSET_MAX = int(os.getenv("TELEGRAM_OFFSET_MAX") or "0")

class TelegramClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        
        # Configure Proxy
        proxy_url = os.getenv("TELEGRAM_PROXY_URL") or os.getenv("HTTPS_PROXY")
        if proxy_url:
            self.session.proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            logger.info(f"[Telegram] Proxy configured: {proxy_url}")
            
    def get_me(self) -> Optional[Dict]:
        try:
            resp = self.session.get(f"{self.base_url}/getMe", timeout=10)
            if resp.status_code == 200:
                return resp.json().get("result")
            else:
                logger.error(f"[Telegram] getMe failed: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"[Telegram] getMe error: {e}")
            return None

    def get_updates(self, offset: Optional[int] = None, timeout: int = 20) -> List[Dict]:
        try:
            params = {"timeout": timeout}
            if offset is not None:
                params["offset"] = offset
                
            resp = self.session.get(f"{self.base_url}/getUpdates", params=params, timeout=timeout + 5)
            if resp.status_code == 200:
                return resp.json().get("result", [])
            elif resp.status_code == 409:
                 # 409 Conflict means either a webhook is active OR another polling instance is running
                 logger.warning(f"[Telegram] Conflict (409): Another bot instance is running or webhook is active. Polling failed.")
                 return []
            else:
                logger.error(f"[Telegram] getUpdates failed ({resp.status_code}): {resp.text}")
                return []
        except Exception as e:
            # Don't log read timeout as error, it happens during long polling
            if "Read timed out" in str(e):
                return []
            logger.error(f"[Telegram] getUpdates connection error: {e}")
            return []

    def get_file_info(self, file_id: str) -> Optional[Dict]:
        try:
            resp = self.session.get(f"{self.base_url}/getFile", params={"file_id": file_id}, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("result")
            return None
        except Exception as e:
            logger.error(f"[Telegram] getFile error: {e}")
            return None

    def download_file(self, file_path_remote: str, local_path: str) -> bool:
        try:
            file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path_remote}"
            with self.session.get(file_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"[Telegram] Download failed: {e}")
            return False

    def send_message(self, chat_id: str, text: str) -> bool:
        try:
            data = {"chat_id": chat_id, "text": text}
            resp = self.session.post(f"{self.base_url}/sendMessage", json=data, timeout=10)
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"[Telegram] sendMessage failed: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"[Telegram] sendMessage error: {e}")
            return False

# Initialize Client
bot_client = None
if TELEGRAM_BOT_TOKEN:
    bot_client = TelegramClient(TELEGRAM_BOT_TOKEN)
    me = bot_client.get_me()
    if me:
        logger.info(f"[Telegram] Bot initialized: {me.get('first_name')} (@{me.get('username')})")
    else:
        logger.warning("[Telegram] Bot initialized but failed to connect (check proxy/token).")

import asyncio # Add asyncio import here

async def send_telegram_message(chat_id: str, text: str) -> bool:
    """
    发送 Telegram 消息 (全局辅助函数)
    """
    if not bot_client:
        logger.warning("[Telegram] Bot not initialized, cannot send message.")
        return False
    # Use asyncio.to_thread for synchronous requests.post
    return await asyncio.to_thread(bot_client.send_message, chat_id, text)


async def send_admin_notification(text: str) -> bool:
    """
    发送通知给预设的管理员
    """
    admin_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not admin_chat_id:
        logger.warning("[Telegram] TELEGRAM_CHAT_ID not set, cannot send admin notification.")
        return False
    
    logger.info(f"[Telegram] Sending admin notification to chat_id: {admin_chat_id}")
    return await send_telegram_message(chat_id=admin_chat_id, text=text)


def download_telegram_file(file_id: str, msg_id: str) -> Optional[str]:
    """
    下载 Telegram 文件到本地 (Using requests)
    """
    if not bot_client:
        return None

    try:
        # Get file info
        f_info = bot_client.get_file_info(file_id)
        if not f_info:
            return None

        file_path_remote = f_info.get('file_path', '')
        _, ext = os.path.splitext(file_path_remote)
        if not ext:
            ext = ".jpg" # Default fallback

        # 确保目录存在
        os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

        filename = f"tg_{msg_id}_{int(time.time())}{ext}"
        local_path = os.path.join(IMAGE_SAVE_DIR, filename)

        logger.info(f"[Telegram] Downloading file to {local_path}...")

        if bot_client.download_file(file_path_remote, local_path):
            return local_path
        return None
    except Exception as e:
        logger.error(f"[Telegram] Download wrapper error: {e}")
        return None


def parse_telegram_link(url: str) -> Optional[tuple]:
    """
    解析 Telegram 消息链接，提取 chat_id 和 message_id

    支持格式:
    - https://t.me/c/{chat_id}/{message_id} (超级群组/频道)
    - https://t.me/{username}/{message_id} (公开群/用户)

    Returns:
        (chat_id: str, message_id: str) 或 None
    """
    import re

    # 匹配 https://t.me/c/{chat_id}/{message_id} 格式
    # chat_id 可能是负数形式（如 -100123456）
    match = re.match(r'https?://t\.me/c/(-?\d+)/(\d+)', url, re.IGNORECASE)
    if match:
        chat_id = match.group(1)
        message_id = match.group(2)
        # 超级群组/频道的 chat_id 需要是负数
        if not chat_id.startswith('-'):
            chat_id = f"-{chat_id}"
        logger.info(f"[Telegram] Parsed link: chat_id={chat_id}, message_id={message_id}")
        return (chat_id, message_id)

    # 匹配 https://t.me/{username}/{message_id} 格式
    match = re.match(r'https?://t\.me/([a-zA-Z0-9_]+)/(\d+)', url, re.IGNORECASE)
    if match:
        username = match.group(1)
        message_id = match.group(2)
        # 需要通过 username 查询 chat_id
        # 对于 Bot API，我们返回 username 格式
        logger.info(f"[Telegram] Parsed link: username={username}, message_id={message_id}")
        return (f"@{username}", message_id)

    return None


def download_media_from_link_sync(url: str) -> Optional[str]:
    """
    从 Telegram 消息链接下载媒体文件（同步版本）

    默认使用 TDL (MTProto) 下载，支持私有频道和公开频道。

    Args:
        url: Telegram 消息链接

    Returns:
        本地文件路径，失败返回 None
    """
    # 直接使用 TDL 下载
    local_path = download_media_via_tdl(url)
    if local_path:
        return local_path

    logger.warning(f"[Telegram] TDL download failed for: {url}")
    return None


def _download_media_via_bot_api(url: str, chat_id: str, message_id: str) -> Optional[str]:
    """
    通过 Bot API 获取消息并下载媒体
    """
    try:
        # 使用 Bot API 获取消息
        # 注意: Bot API 对于公开链接可以直接访问
        resolved_chat_id = chat_id

        if chat_id.startswith('@'):
            # 公开用户名，需要使用 getChat 解析
            username = chat_id[1:]
            resp = bot_client.session.get(
                f"{bot_client.base_url}/getChat",
                params={"chat_id": f"@{username}"},
                timeout=10
            )
            if resp.status_code != 200:
                logger.warning(f"[Telegram] Failed to get chat info: {resp.text[:200]}")
                return None
            chat_info = resp.json().get("result", {})
            resolved_chat_id = str(chat_info.get("id"))
            logger.info(f"[Telegram] Resolved username to chat_id: {resolved_chat_id}")

        # 使用 getMessages 获取消息详情
        try:
            chat_id_int = int(resolved_chat_id)
        except ValueError:
            logger.error(f"[Telegram] Invalid chat_id format: {resolved_chat_id}")
            return None

        resp = bot_client.session.get(
            f"{bot_client.base_url}/getMessages",
            params={"chat_id": chat_id_int, "message_ids": message_id},
            timeout=10
        )

        if resp.status_code != 200:
            logger.warning(f"[Telegram] getMessages failed ({resp.status_code}): {resp.text[:200]}")
            return None

        result = resp.json().get("result", {})
        if not result:
            logger.warning(f"[Telegram] No message found")
            return None

        # 获取第一条消息
        messages = result if isinstance(result, list) else [result]
        if not messages:
            logger.warning(f"[Telegram] Empty message list")
            return None

        msg = messages[0]

        # 检查消息中的媒体类型
        local_path = None

        # 图片
        if "photo" in msg:
            photos = msg["photo"]
            best_photo = photos[-1] if isinstance(photos, list) else photos
            file_id = best_photo["file_id"] if isinstance(best_photo, dict) else best_photo
            local_path = download_telegram_file(file_id, message_id)
            if local_path:
                logger.info(f"[Telegram] Downloaded photo from link: {local_path}")
            return local_path

        # 视频
        if "video" in msg:
            video = msg["video"]
            file_id = video["file_id"] if isinstance(video, dict) else video
            local_path = download_telegram_file(file_id, message_id)
            if local_path:
                logger.info(f"[Telegram] Downloaded video from link: {local_path}")
            return local_path

        # 文件/文档
        if "document" in msg:
            doc = msg["document"]
            file_id = doc["file_id"] if isinstance(doc, dict) else doc
            local_path = download_telegram_file(file_id, message_id)
            if local_path:
                logger.info(f"[Telegram] Downloaded document from link: {local_path}")
            return local_path

        logger.info(f"[Telegram] No media found in message")
        return None

    except Exception as e:
        logger.error(f"[Telegram] Bot API method failed: {e}")
        return None


def _download_media_via_web(url: str, message_id: str) -> Optional[str]:
    """
    通过网页解析获取 Telegram 消息的媒体文件

    注意：Telegram 网页版只能获取公开频道的消息，私有频道需要 Bot API
    """
    try:
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        with httpx.Client(timeout=15) as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"[Telegram] Web fetch failed: HTTP {response.status_code}")
                return None

            # 尝试从页面中提取媒体 URL
            html = response.text

            # 查找 og:image 或 twitter:image
            import re

            # og:image
            og_image_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.IGNORECASE)
            if og_image_match:
                image_url = og_image_match.group(1)
                logger.info(f"[Telegram] Found og:image: {image_url}")
                return _download_image_from_url(image_url, message_id)

            # 查找 data-src (懒加载图片)
            lazy_image_match = re.search(r'data-src="([^"]+telesco\.pe[^"]+)"', html, re.IGNORECASE)
            if lazy_image_match:
                image_url = lazy_image_match.group(1)
                logger.info(f"[Telegram] Found lazy image: {image_url}")
                return _download_image_from_url(image_url, message_id)

            # 查找 TG 信使的媒体 URL
            tg_media_match = re.search(r'(https?://[^"]+\.telesco\.pe[^"]+)', html)
            if tg_media_match:
                media_url = tg_media_match.group(1)
                logger.info(f"[Telegram] Found telesco.pe media: {media_url}")
                return _download_image_from_url(media_url, message_id)

            logger.info(f"[Telegram] No media found in webpage")
            return None

    except Exception as e:
        logger.error(f"[Telegram] Web scraping failed: {e}")
        return None


def _download_image_from_url(image_url: str, msg_id: str) -> Optional[str]:
    """
    从 URL 下载图片到本地
    """
    try:
        import httpx
        import os

        with httpx.Client(timeout=30) as client:
            response = client.get(image_url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"[Telegram] Failed to download image: HTTP {response.status_code}")
                return None

            # 确定文件扩展名
            ext = ".jpg"
            content_type = response.headers.get("content-type", "")
            if "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            elif "video" in content_type or "mp4" in content_type:
                ext = ".mp4"

            # 保存到本地
            os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
            filename = f"tg_{msg_id}_{int(time.time())}{ext}"
            local_path = os.path.join(IMAGE_SAVE_DIR, filename)

            with open(local_path, "wb") as f:
                f.write(response.content)

            logger.info(f"[Telegram] Downloaded image to: {local_path}")
            return local_path

    except Exception as e:
        logger.error(f"[Telegram] Image download failed: {e}")
        return None


async def download_media_from_link(url: str) -> Optional[str]:
    """
    从 Telegram 消息链接下载媒体文件（异步版本）

    Args:
        url: Telegram 消息链接

    Returns:
        本地文件路径，失败返回 None
    """
    return await asyncio.to_thread(download_media_from_link_sync, url)


def download_media_via_tdl(url: str) -> Optional[str]:
    """
    使用 TDL (MTProto) 下载 Telegram 私有频道媒体

    TDL 使用用户协议而非 Bot API，可以访问私有频道。
    TDL v0.20+ 使用默认的 /root/.tdl 目录存储配置和会话。

    Args:
        url: Telegram 消息链接

    Returns:
        本地文件路径，失败返回 None
    """
    import os
    import subprocess
    import glob

    download_dir = os.getenv("TDL_DOWNLOAD_DIR", "/app/data/telegram_media")

    # 确保下载目录存在
    os.makedirs(download_dir, exist_ok=True)

    # 检查 tdl 是否可用
    if not os.path.exists("/usr/local/bin/tdl"):
        logger.warning("[Telegram] TDL not installed, skipping")
        return None

    # 检查 TDL 是否已登录（通过检查配置文件）
    tdl_dir = os.path.expanduser("~/.tdl")
    if not os.path.exists(os.path.join(tdl_dir, "data.kv")):
        logger.warning(f"[Telegram] TDL not logged in (no data.kv found in {tdl_dir})")
        logger.info("[Telegram] Please login first: tdl login")
        return None

    # 获取代理配置
    proxy_url = os.getenv("TELEGRAM_PROXY_URL", "")

    try:
        logger.info(f"[Telegram] Downloading via TDL: {url}")

        # 获取下载前已存在的文件列表
        existing_files = set(glob.glob(os.path.join(download_dir, "*")))

        # 构建 tdl 命令
        cmd = [
            "tdl", "dl",
            "-u", url,
            "-d", download_dir,
            "--limit", "1"
        ]

        # 添加代理配置
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])
            logger.info(f"[Telegram] Using proxy: {proxy_url}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )

        if result.returncode != 0:
            logger.error(f"[Telegram] TDL download failed: {result.stderr}")
            return None

        # 查找新下载的文件
        new_files = set(glob.glob(os.path.join(download_dir, "*"))) - existing_files

        if new_files:
            downloaded_file = list(new_files)[0]
            logger.info(f"[Telegram] TDL downloaded: {downloaded_file}")
            return downloaded_file
        else:
            logger.warning("[Telegram] TDL completed but no file found")
            return None

    except subprocess.TimeoutExpired:
        logger.error("[Telegram] TDL download timed out")
        return None
    except Exception as e:
        logger.error(f"[Telegram] TDL download error: {e}")
        return None


async def download_media_from_link_via_tdl(url: str) -> Optional[str]:
    """
    异步使用 TDL 下载 Telegram 私有频道媒体
    """
    return await asyncio.to_thread(download_media_via_tdl, url)


def parse_telegram_message(msg: Dict[str, Any]) -> Optional[UnifiedMessage]:
    """
    解析 Telegram 消息字典为 UnifiedMessage
    """
    try:
        msg_id = str(msg.get("message_id"))
        from_user_obj = msg.get("from", {})
        from_user = from_user_obj.get("username") or f"{from_user_obj.get('first_name')} {from_user_obj.get('last_name', '')}".strip()
        chat_timestamp = msg.get("date", int(time.time()))
        
        unified_msg = None
        
        if "text" in msg:
            text_content = msg["text"]
            
            # Check if text is a URL
            import re
            url_pattern = re.compile(r'^(https?://[^\s]+)$', re.IGNORECASE)
            
            if url_pattern.match(text_content.strip()):
                # URL link message
                unified_msg = UnifiedMessage(
                    msg_id=msg_id,
                    source="telegram",
                    msg_type="link",
                    content=text_content.strip(),
                    from_user=from_user,
                    create_time=chat_timestamp,
                    raw_data={"message": msg}
                )
            else:
                # Normal text message
                unified_msg = UnifiedMessage(
                    msg_id=msg_id,
                    source="telegram",
                    msg_type="text",
                    content=text_content,
                    from_user=from_user,
                    create_time=chat_timestamp,
                    raw_data={"message": msg}
                )
            
        elif "photo" in msg:
            # 图片消息 (取最大尺寸)
            photos = msg["photo"]
            best_photo = photos[-1]
            file_id = best_photo["file_id"]
            
            # 下载图片
            local_path = download_telegram_file(file_id, msg_id)
            if local_path:
                unified_msg = UnifiedMessage(
                    msg_id=msg_id,
                    source="telegram",
                    msg_type="image",
                    content=local_path,
                    from_user=from_user,
                    create_time=chat_timestamp,
                    raw_data={"message": msg}
                )
            else:
                logger.error(f"[Telegram] Failed to download photo for msg {msg_id}")
        
        elif "video" in msg:
            # 视频消息
            video = msg["video"]
            file_id = video["file_id"]
            
            local_path = download_telegram_file(file_id, msg_id)
            if local_path:
                unified_msg = UnifiedMessage(
                    msg_id=msg_id,
                    source="telegram",
                    msg_type="video",
                    content=local_path,
                    from_user=from_user,
                    create_time=chat_timestamp,
                    raw_data={"message": msg, "file": {"filename": video.get("file_name", os.path.basename(local_path))}}
                )
            else:
                logger.error(f"[Telegram] Failed to download video for msg {msg_id}")

        elif "document" in msg:
            # 文件消息
            doc = msg["document"]
            file_id = doc["file_id"]
            file_name = doc.get("file_name", "unknown_file")
            
            local_path = download_telegram_file(file_id, msg_id)
            if local_path:
                unified_msg = UnifiedMessage(
                    msg_id=msg_id,
                    source="telegram",
                    msg_type="file",
                    content=local_path,
                    from_user=from_user,
                    create_time=chat_timestamp,
                    raw_data={"message": msg, "file": {"filename": file_name}}
                )
            else:
                logger.error(f"[Telegram] Failed to download document for msg {msg_id}")

        return unified_msg
    except Exception as e:
        logger.error(f"[Telegram] Parse error: {e}")
        return None

def get_last_offset() -> Optional[int]:
    """
    获取上次的 offset，优先使用配置中的最大偏移量
    """
    file_offset = None
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    file_offset = int(content)
                    logger.info(f"[Telegram] Loaded last offset from {OFFSET_FILE}: {file_offset}")
        except Exception as e:
            logger.error(f"Error reading offset file: {e}")

    # 如果配置了最大偏移量且大于文件中的值，使用配置的值
    if TELEGRAM_OFFSET_MAX > 0:
        if file_offset is None or TELEGRAM_OFFSET_MAX > file_offset:
            logger.info(f"[Telegram] Using configured max offset: {TELEGRAM_OFFSET_MAX} (file offset: {file_offset})")
            return TELEGRAM_OFFSET_MAX

    return file_offset

def save_last_offset(offset: int):
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(str(offset))
    except Exception as e:
        logger.error(f"Error saving offset file: {e}")

async def run_telegram_polling():
    """
    Telegram 轮询主循环 (Using requests)
    """
    from src.services.message_processor import process_message

    logger.info(">>> Telegram Service v2.0 (Requests-based) Starting... <<<")

    if not bot_client:
        logger.warning("[Telegram] Token not configured, polling disabled.")
        return

    logger.info("[Telegram] Starting Polling Service (requests)...")
    offset = get_last_offset()

    # Track when we last logged a "no updates" message to avoid spam
    last_no_update_log = 0

    while True:
        try:
            poll_logger.debug(f"[Telegram Polling] Calling getUpdates with offset={offset}...")

            # Using a timeout for long polling
            updates = await asyncio.to_thread(bot_client.get_updates, offset=offset, timeout=20)

            if updates:
                poll_logger.info(f"[Telegram Polling] Successfully pulled {len(updates)} updates from server")
                for update in updates:
                    update_id = update["update_id"]
                    # 输出完整的消息报文（JSON 格式化）
                    poll_logger.debug(f"[Telegram Polling] Raw message: {json.dumps(update, ensure_ascii=False, indent=2)}")

                    if "message" in update:
                        msg_data = update["message"]
                        from_info = msg_data.get("from", {})
                        username = from_info.get("username") or from_info.get("first_name", "Unknown")
                        text_preview = msg_data.get("text", "[Media/Other]")[:50]

                        poll_logger.info(f"[Telegram Polling] Processing message {msg_data.get('message_id')} from @{username}: {text_preview}")

                        unified_msg = parse_telegram_message(msg_data)
                        if unified_msg:
                            await process_message(unified_msg)
                        else:
                            poll_logger.info(f"[Telegram Polling] Message skipped or failed to parse (ID: {msg_data.get('message_id')})")
                    else:
                        # Could be edited_message, channel_post, callback_query, etc.
                        update_types = [k for k in update.keys() if k != "update_id"]
                        poll_logger.info(f"[Telegram Polling] Received non-message update: {update_types}")

                    # Update offset to next one
                    offset = update_id + 1
                    save_last_offset(offset)
            else:
                # No updates, wait a bit
                current_time = time.time()
                if current_time - last_no_update_log > 300: # Log "still polling" every 5 minutes at INFO level
                    poll_logger.info("[Telegram Polling] Active, no new messages in the last 5 minutes.")
                    last_no_update_log = current_time
                await asyncio.sleep(1)

        except Exception as e:
            poll_logger.error(f"[Telegram Polling] Loop error: {e}", exc_info=True)
            await asyncio.sleep(10) # Wait longer on error