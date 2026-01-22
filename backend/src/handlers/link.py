import logging
import re
import os
import requests
from bs4 import BeautifulSoup
from src.handlers.base import BaseHandler
from src.models.chat_record import UnifiedMessage
from src.services.craft import save_blocks_to_craft
from src.services.formatter import format_unified_message_as_craft_blocks
from src.services.cos import upload_file
# crew_link_summary 的导入延迟到函数内部，避免与 WeCom SDK 加载冲突
# telegram 的导入也延迟到函数内部，避免循环导入

logger = logging.getLogger(__name__)


def is_telegram_link(url: str) -> bool:
    """检查是否是 Telegram 消息链接"""
    return bool(re.match(r'https?://t\.me/', url, re.IGNORECASE))


class LinkHandler(BaseHandler):
    """
    处理链接类消息
    Priority: 1 (High)
    """
    async def check(self, msg: UnifiedMessage) -> bool:
        # 1. 直接是 link 类型
        if msg.msg_type == "link":
            return True
        # 2. 文本中包含 http/https
        if msg.msg_type == "text" and ("http://" in msg.content or "https://" in msg.content):
            return True
        return False

    async def handle(self, msg: UnifiedMessage):
        logger.info(f"[LinkHandler] Processing link message: {msg.msg_id}")

        # 提取 URL (简单假设 content 就是 URL，或者包含 URL)
        # 如果是混合文本，这里做一个简单的提取第一个 URL 的操作
        url_pattern = re.compile(r'https?://[^\s]+')
        match = url_pattern.search(msg.content)
        if not match:
            logger.warning("[LinkHandler] No URL found in content")
            return

        url = match.group(0).rstrip('.,;!?')  # 移除末尾标点

        # 处理 Telegram 链接
        if is_telegram_link(url):
            await self._handle_telegram_link(msg, url)
            return

        title = "未知链接"
        page_content = ""

        # 企微消息：先尝试从 raw_data 提取标题，再抓取页面内容用于摘要
        if msg.source == 'wecom' and msg.raw_data and 'link' in msg.raw_data:
            wecom_title = msg.raw_data['link'].get('title')
            if wecom_title:
                title = wecom_title
                logger.info(f"[LinkHandler] Using WeCom title: {title}")

        # 无论是否获取到标题，都需要抓取页面内容用于生成摘要
        try:
            logger.info(f"[LinkHandler] Fetching content for: {url}")
            # 设置 User-Agent 防止被拦截
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                # 尝试解码，处理可能的乱码
                resp.encoding = resp.apparent_encoding
                soup = BeautifulSoup(resp.text, 'html.parser')
                # 如果企微没提供标题，则从页面提取
                if title == "未知链接" and soup.title and soup.title.string:
                    title = soup.title.string.strip()
                    logger.info(f"[LinkHandler] Using page title: {title}")
                # 提取页面主要文本内容用于摘要
                # 移除脚本和样式
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                page_content = soup.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.error(f"[LinkHandler] Failed to fetch content: {e}")

        # 1. 保存到 Craft
        blocks = format_unified_message_as_craft_blocks(msg)
        success = await save_blocks_to_craft(blocks)

        # 2. 生成摘要（延迟导入 crewai 相关模块，避免与 WeCom SDK 冲突）
        summary = None
        if page_content:
            try:
                from src.agents.link_summary import run_link_summary
                summary = run_link_summary(url, page_content, title)
            except Exception as e:
                logger.error(f"[LinkHandler] Summary generation failed: {e}")

        # 3. 回复用户
        if success:
            reply_text = f"已保存文章：{title}"
            if summary:
                reply_text += f"\n\n📝 摘要：{summary}"
            reply_text += "\n\n请在笔记收件箱中阅读"
            await self.reply(msg, reply_text)
        else:
            await self.reply(msg, "⚠️ 链接保存失败")

    async def _handle_telegram_link(self, msg: UnifiedMessage, url: str):
        """
        处理 Telegram 消息链接：下载媒体、上传 COS、保存到 Craft
        """
        from src.services.telegram import download_media_from_link

        logger.info(f"[LinkHandler] Processing Telegram link: {url}")

        try:
            # 1. 从链接下载媒体文件
            local_path = await download_media_from_link(url)
            if not local_path:
                logger.warning(f"[LinkHandler] No media found or download failed, saving as link")
                # 没有媒体，保存为普通链接
                blocks = format_unified_message_as_craft_blocks(msg)
                success = await save_blocks_to_craft(blocks)
                await self.reply(msg, "已保存 Telegram 链接到收件箱" if success else "⚠️ 保存失败")
                return

            logger.info(f"[LinkHandler] Downloaded media to: {local_path}")

            # 2. 上传到 COS
            cos_url = upload_file(local_path)
            if not cos_url:
                logger.error(f"[LinkHandler] COS upload failed, trying to use local path")
                cos_url = local_path

            # 3. 删除本地临时文件
            try:
                os.remove(local_path)
                logger.info(f"[LinkHandler] Removed local file: {local_path}")
            except Exception as e:
                logger.warning(f"[LinkHandler] Failed to remove local file: {e}")

            logger.info(f"[LinkHandler] Media uploaded to COS: {cos_url}")

            # 4. 保存到 Craft (使用 image block)
            blocks = [{
                "type": "image",
                "url": cos_url
            }, {
                "type": "text",
                "markdown": f"Telegram 消息: {url}"
            }]
            success = await save_blocks_to_craft(blocks)

            # 5. 回复用户
            if success:
                await self.reply(msg, "已保存 Telegram 媒体到收件箱，期待你的查看")
            else:
                await self.reply(msg, "⚠️ Telegram 媒体保存失败")

        except Exception as e:
            logger.error(f"[LinkHandler] Telegram link processing failed: {e}")
            # 出错时保存为普通链接
            blocks = format_unified_message_as_craft_blocks(msg)
            success = await save_blocks_to_craft(blocks)
            await self.reply(msg, "已保存 Telegram 链接到收件箱" if success else "⚠️ 处理失败")