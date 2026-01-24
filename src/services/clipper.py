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
            # 不手动设置编码，让 requests 自动处理
            # 如果需要指定编码，从响应头或 meta 标签中读取
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
        从 HTML 提取正文内容，优先使用直接提取避免编码问题

        Args:
            html: 网页 HTML
            url: 原始 URL（用于处理相对路径）

        Returns:
            提取结果 dict，失败返回 None
        """
        try:
            # 使用 html.parser 解析器，避免 lxml 的编码问题
            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = (soup.find('title') and soup.find('title').get_text(strip=True)) or ""

            # 直接从原始 HTML 提取内容元素列表，避免编码问题
            content_elements = self._extract_content_elements(soup, url)

            return {
                "title": title,
                "short_title": title[:50] if title else "",
                "content_elements": content_elements,
                "byline": "",
            }
        except Exception as e:
            logger.warning(f"[Clipper] 内容提取失败: {e}")
            return None

    def _extract_content_elements(self, soup: BeautifulSoup, url: str) -> List[BeautifulSoup]:
        """
        直接从原始 HTML 提取文章内容元素

        Args:
            soup: BeautifulSoup 对象
            url: 原始 URL

        Returns:
            BeautifulSoup 元素列表
        """
        # 优先查找微信公众号文章内容区域
        article = (soup.find('div', id='js_content') or  # 微信公众号
                   soup.find('article') or
                   soup.find('div', class_=lambda x: x and 'article' in str(x).lower()) or
                   soup.find('div', id=lambda x: x and 'article' in str(x).lower()) or
                   soup.find('main') or
                   soup.find('div', role='main') or
                   soup.find('div', class_=lambda x: x and 'content' in str(x).lower()))

        elements = []
        if article:
            # 提取各级标题和段落
            for elem in article.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                          'p', 'pre', 'blockquote', 'ul', 'ol']):
                text = elem.get_text(strip=True)
                if text and len(text) >= 5:
                    elements.append(elem)

        # 兜底：尝试提取所有段落
        if not elements:
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 10:
                    elements.append(p)

        return elements

    def elements_to_blocks(self, elements: List, base_url: str) -> List[Dict]:
        """
        将 HTML 元素列表转换为 Craft blocks

        Args:
            elements: BeautifulSoup 元素列表
            base_url: 基础 URL（用于处理相对路径）

        Returns:
            Craft blocks 列表
        """
        if not elements:
            return []

        blocks = []

        for elem in elements:
            if not hasattr(elem, 'name'):
                continue

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

            elif tag_name == 'p':
                text = elem.get_text(strip=True)
                if text:
                    blocks.append({
                        "type": "text",
                        "markdown": text
                    })

            elif tag_name == 'ul':
                for li in elem.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        blocks.append({
                            "type": "text",
                            "markdown": "- " + text
                        })

            elif tag_name == 'ol':
                for i, li in enumerate(elem.find_all('li', recursive=False), 1):
                    text = li.get_text(strip=True)
                    if text:
                        blocks.append({
                            "type": "text",
                            "markdown": f"{i}. " + text
                        })

            elif tag_name == 'blockquote':
                text = elem.get_text(strip=True)
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip():
                            blocks.append({
                                "type": "text",
                                "markdown": "> " + line.strip()
                            })

            elif tag_name == 'pre':
                code_text = elem.get_text('\n')
                if code_text.strip():
                    blocks.append({
                        "type": "text",
                        "markdown": f"```\n{code_text}\n```"
                    })

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

        # 步骤2：提取正文元素
        content = self.extract_content(html, url)
        elements = content.get("content_elements", []) if content else []
        if not elements:
            logger.info(f"[Clipper] 提取正文失败，返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        # 检查内容是否为空（只有很少的内容）
        text_content = "".join([e.get_text(strip=True) for e in elements])
        if len(text_content) < 50:
            logger.info(f"[Clipper] 正文内容过短（{len(text_content)} 字符），返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        # 步骤3：将元素转换为 blocks
        blocks = self.elements_to_blocks(elements, url)

        if not blocks:
            logger.info(f"[Clipper] 未提取到有效内容，返回链接 block: {url}")
            return self._create_fallback_block(fallback_url or url)

        # 步骤4：从原始 HTML 补充图片（针对微信公众号等平台的特殊处理）
        original_soup = BeautifulSoup(html, "html.parser")
        extra_images = self._extract_images_from_html(original_soup, url)

        # 将额外图片插入到 blocks 中（放在第一个位置之后）
        if extra_images:
            insert_idx = 1
            for i, b in enumerate(blocks):
                if b.get("type") == "text" and b.get("markdown"):
                    insert_idx = i + 1
                    break
            blocks[insert_idx:insert_idx] = extra_images
            logger.info(f"[Clipper] 补充了 {len(extra_images)} 张图片")

        logger.info(f"[Clipper] 成功提取: {content['title']}, {len(blocks)} blocks")

        # 步骤5：构建 Page Block
        # 如果标题为空，使用 URL 作为标题
        page_title = content["title"] or url
        page_block = {
            "type": "page",
            "textStyle": "page",
            "markdown": page_title,
            "content": blocks
        }

        return [page_block]

    def _extract_images_from_html(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        从原始 HTML 中提取图片

        针对微信公众号等平台，图片可能在 data-img、data-src 等属性中

        Args:
            soup: BeautifulSoup 对象
            base_url: 基础 URL

        Returns:
            图片 blocks 列表
        """
        image_blocks = []
        seen_urls = set()

        # 方法1: 查找 data-img 属性（微信公众号常用）
        for tag in soup.find_all(attrs={'data-img': True}):
            img_url = tag.get('data-img')
            if img_url and img_url not in seen_urls:
                full_url = urljoin(base_url, img_url)
                if full_url.startswith('http'):
                    image_blocks.append({
                        "type": "image",
                        "url": full_url,
                        "markdown": f"![Image]({full_url})"
                    })
                    seen_urls.add(img_url)

        # 方法2: 查找普通 img 标签
        for img in soup.find_all('img'):
            src = (img.get('src') or img.get('data-src') or img.get('data-original')
                   or img.get('data-watermark-src'))
            if src and src not in seen_urls:
                full_url = urljoin(base_url, src)
                if full_url.startswith('http') and not full_url.startswith('data:'):
                    image_blocks.append({
                        "type": "image",
                        "url": full_url,
                        "markdown": f"![Image]({full_url})"
                    })
                    seen_urls.add(src)

        return image_blocks

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
