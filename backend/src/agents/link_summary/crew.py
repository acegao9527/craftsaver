"""
链接摘要 Crew
用于分析链接内容，生成 100 字左右的中文摘要
"""
import re
import json
import logging
from typing import Dict, Any, Optional
from crewai import Agent, Crew, Process, Task, LLM
from ..base.config import Config

logger = logging.getLogger(__name__)


class LinkSummaryCrew:
    """链接摘要生成 Crew"""

    def __init__(self):
        self.llm = LLM(
            model=Config.OPENAI_MODEL_NAME,
            base_url=Config.OPENAI_API_BASE,
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3
        )

    def run(self, url: str, content: str, title: str = "") -> Optional[Dict[str, Any]]:
        """
        生成链接摘要

        Args:
            url: 链接地址
            content: 页面提取的文本内容
            title: 页面标题

        Returns:
            Dict: 包含 summary 的结果
        """
        summarizer = Agent(
            role="内容摘要助手",
            goal="为文章生成简洁的中文摘要",
            backstory="""你是一个专业的内容摘要助手，善于提取文章的核心信息，
            并将其浓缩为简洁的中文摘要。你的摘要准确、精炼，能让读者快速了解文章要点。""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        task_summary = Task(
            description=f"""请分析以下链接内容，生成约 100 字的中文摘要。

## 链接信息
- 标题：{title}
- URL：{url}

## 页面内容（全文）
{content[:15000]}

## 要求
1. 仔细阅读页面内容，提取核心观点和关键信息
2. 摘要长度控制在 100 字左右
3. 使用中文输出
4. 不要包含「标题」、「链接」等前缀，直接输出摘要内容
5. 如果内容无法理解或太短，返回 "null"

请以 JSON 格式输出：
{{
  "summary": "生成的摘要内容，或为 null 如果无法生成"
}}""",
            agent=summarizer,
            expected_output="JSON 格式的摘要结果"
        )

        crew = Crew(
            agents=[summarizer],
            tasks=[task_summary],
            process=Process.sequential,
            verbose=False
        )

        logger.info(f"[LinkSummaryCrew] 开始生成摘要: {url[:50]}...")
        try:
            result = crew.kickoff()
            logger.info(f"[LinkSummaryCrew] 摘要生成完成")
            return self._parse_result(result)
        except Exception as e:
            logger.error(f"[LinkSummaryCrew] 生成失败: {e}")
            return None

    def _parse_result(self, result) -> Optional[Dict[str, Any]]:
        """解析 Crew 输出为 JSON"""
        try:
            text = str(result)
            logger.debug(f"[LinkSummaryCrew] 原始输出: {text[:300]}...")

            if not text or text.strip() == "":
                logger.warning("[LinkSummaryCrew] 输出为空")
                return None

            # 尝试直接解析
            try:
                data = json.loads(text)
                summary = data.get("summary")
                if summary and summary.lower() != "null":
                    return {"summary": summary}
            except json.JSONDecodeError:
                pass

            # 清理 markdown 代码块
            cleaned = re.sub(r'```json?\n?', '', text)
            cleaned = re.sub(r'```\n?', '', cleaned)
            cleaned = cleaned.strip()

            # 尝试提取 JSON（可能在思考过程后面）
            json_match = re.search(r'\{\s*"summary"\s*:\s*"[^"]*"\s*\}', cleaned)
            if json_match:
                data = json.loads(json_match.group())
                summary = data.get("summary")
                if summary and summary.lower() != "null":
                    return {"summary": summary}

            if not cleaned:
                logger.warning("[LinkSummaryCrew] 清理后内容为空")
                return None

            data = json.loads(cleaned)
            summary = data.get("summary")

            if summary and summary.lower() != "null":
                return {"summary": summary}
            return None

        except json.JSONDecodeError as e:
            logger.error(f"[LinkSummaryCrew] JSON 解析失败: {e}, raw: {text[:200]}")
            return None
        except Exception as e:
            logger.error(f"[LinkSummaryCrew] 解析异常: {e}")
            return None


def run_link_summary(url: str, content: str, title: str = "") -> Optional[str]:
    """
    顶层函数：生成链接摘要

    Args:
        url: 链接地址
        content: 页面文本内容
        title: 页面标题

    Returns:
        str: 摘要内容，或 None
    """
    crew = LinkSummaryCrew()
    result = crew.run(url, content, title)
    if result:
        return result.get("summary")
    return None
