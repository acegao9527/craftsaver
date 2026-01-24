"""
网页剪藏服务模块

将网页内容抓取并转换为 Craft Page Block 格式
"""
import logging
import uuid
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger(__name__)


class WebClipper:
    """网页剪藏服务"""

    def __init__(self, timeout: int = 15):
        """
        初始化剪藏服务

        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def fetch_page(self, url: str) -> Optional[str]:
        """
        获取网页 HTML 内容

        Args:
            url: 网页 URL

        Returns:
            HTML 内容，失败返回 None
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            # 检测编码
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.exceptions.Timeout:
            logger.warning(f"[Clipper] 请求超时: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[Clipper] HTTP 错误: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"[Clipper] 请求异常: {e}")
            return None

    def extract_content(self, html: str, url: str) -> Optional[Dict]:
        """
        使用 readability 提取正文内容

        Args:
            html: 网页 HTML
            url: 原始 URL（用于处理相对路径）

        Returns:
            提取结果 dict，失败返回 None
        """
        try:
            doc = Document(html, url)
            # 使用 getattr 兼容不同版本的 readability
            byline = getattr(doc, 'byline', lambda: "")() or ""
            return {
                "title": doc.title() or "",
                "short_title": doc.short_title() or "",
                "content_html": doc.summary(),
                "byline": byline,
            }
        except Exception as e:
            logger.warning(f"[Clipper] 内容提取失败: {e}")
            return None

    def html_to_blocks(self, content_html: str, base_url: str) -> List[Dict]:
        """
        将 HTML 内容转换为 Craft blocks

        Args:
            content_html: 正文的 HTML
            base_url: 基础 URL（用于处理相对路径）

        Returns:
            Craft blocks 列表
        """
        if not content_html:
            return []

        soup = BeautifulSoup(content_html, "lxml")
        blocks = []

        # 用于跟踪上一个 block，避免空行
        last_was_empty = False

        # 遍历所有元素，按顺序处理
        for elem in soup.find_all(recursive=True):
            # 只处理特定标签
            tag_name = elem.name

            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = elem.get_text(strip=True)
                if text:
                    level = int(tag_name[1])
                    prefix = "#" * level + " "
                    blocks.append({
                        "type": "text",
                        "markdown": prefix + text
                    })
                    last_was_empty = False

            elif tag_name == 'p':
                text = elem.get_text(strip=True)
                if text:
                    blocks.append({
                        "type": "text",
                        "markdown": text
                    })
                    last_was_empty = False
                elif not last_was_empty:
                    # 空段落作为分隔
                    blocks.append({
                        "type": "text",
                        "markdown": ""
                    })
                    last_was_empty = True

            elif tag_name in ['ul', 'ol']:
                # 列表处理
                for li in elem.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        prefix = "- " if tag_name == 'ul' else "1. "
                        blocks.append({
                            "type": "text",
                            "markdown": prefix + text
                        })
                        last_was_empty = False

            elif tag_name == 'blockquote':
                text = elem.get_text(strip=True)
                if text:
                    # 用 > 引用格式
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip():
                            blocks.append({
                                "type": "text",
                                "markdown": "> " + line.strip()
                            })
                    last_was_empty = False

            elif tag_name == 'a':
                # 链接处理
                text = elem.get_text(strip=True)
                href = elem.get('href')
                if text and href:
                    full_url = urljoin(base_url, href)
                    blocks.append({
                        "type": "text",
                        "markdown": f"[{text}]({full_url})"
                    })
                    last_was_empty = False

            elif tag_name == 'code':
                # 行内代码
                text = elem.get_text(strip=True)
                if text and elem.parent and elem.parent.name != 'pre':
                    blocks.append({
                        "type": "text",
                        "markdown": f"`{text}`"
                    })
                    last_was_empty = False

            elif tag_name == 'pre':
                # 代码块
                code_text = elem.get_text('\n')
                if code_text.strip():
                    blocks.append({
                        "type": "text",
                        "markdown": f"```\n{code_text}\n```"
                    })
                    last_was_empty = False

            elif tag_name == 'img':
                src = elem.get('src') or elem.get('data-src') or elem.get('data-original')
                if src:
                    full_url = urljoin(base_url, src)
                    blocks.append({
                        "type": "image",
                        "url": full_url,
                        "markdown": f"![Image]({full_url})"
                    })
                    last_was_empty = False

            elif tag_name in ['br', 'hr']:
                # 换行或分隔线
                if not last_was_empty:
                    blocks.append({
                        "type": "text",
                        "markdown": ""
                    })
                    last_was_empty = True

        # 清理末尾空行
        while blocks and blocks[-1].get("markdown") == "" and len(blocks) > 1:
            blocks.pop()

        return blocks

    def create_page_block(self, url: str, fallback_url: str = None) -> List[Dict]:
        """
        创建网页的 Page Block

        尝试抓取网页内容，成功则返回 Page Block，失败则返回 richUrl block

        Args:
            url: 网页 URL
            fallback_url: 备用 URL（用于记录原始链接）

        Returns:
            Craft blocks 列表（1个 page block 或 1个 richUrl block）
        """
        # 步骤1：获取网页内容
        html = self.fetch_page(url)
        if not html:
            logger.info(f"[Clipper] 获取页面失败，返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        # 步骤2：提取正文
        content = self.extract_content(html, url)
        if not content or not content.get("content_html"):
            logger.info(f"[Clipper] 提取正文失败，返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        # 检查内容是否为空（只有很少的内容）
        soup = BeautifulSoup(content["content_html"], "lxml")
        text_content = soup.get_text(strip=True)
        if len(text_content) < 50:
            logger.info(f"[Clipper] 正文内容过短（{len(text_content)} 字符），返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        # 步骤3：转换为 blocks
        blocks = self.html_to_blocks(content["content_html"], url)

        if not blocks:
            logger.info(f"[Clipper] 未提取到有效内容，返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        logger.info(f"[Clipper] 成功提取: {content['title']}, {len(blocks)} blocks")

        # 步骤4：构建 Page Block
        page_block = {
            "type": "page",
            "textStyle": "page",
            "markdown": content["title"],
            "content": blocks
        }

        return [page_block]

    def _create_fallback_block(self, url: str) -> List[Dict]:
        """
        创建回退的 richUrl block

        Args:
            url: 链接 URL

        Returns:
            richUrl block 列表
        """
        return [{
            "type": "richUrl",
            "url": url
        }]


# 全局剪藏器实例
_clipper = None


def get_clipper() -> WebClipper:
    """获取 WebClipper 实例"""
    global _clipper
    if _clipper is None:
        _clipper = WebClipper()
    return _clipper


def clip_url_to_page_blocks(url: str, fallback_url: str = None) -> List[Dict]:
    """
    将 URL 转换为 Page Block（用于发送到 Craft）

    Args:
        url: 要剪藏的网页 URL
        fallback_url: 备用 URL（记录原始链接）

    Returns:
        Craft blocks 列表
    """
    return get_clipper().create_page_block(url, fallback_url)
