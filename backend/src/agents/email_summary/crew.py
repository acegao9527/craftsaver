"""
邮件摘要 Crew
使用 LLM 对邮件内容生成摘要
"""
import os
import re
import json
import logging
from typing import Optional
from crewai import Agent, Crew, Process, Task, LLM
from src.models.email import EmailSummary
from ..base.config import Config

logger = logging.getLogger(__name__)


class EmailSummaryCrew:
    """邮件摘要 Crew"""

    def __init__(self):
        self.llm = LLM(
            model=Config.OPENAI_MODEL_NAME,
            base_url=Config.OPENAI_API_BASE,
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3
        )

    def run(self, subject: str, content: str) -> Optional[EmailSummary]:
        """
        生成邮件摘要

        Args:
            subject: 邮件主题
            content: 邮件正文

        Returns:
            EmailSummary 或 None（垃圾邮件）
        """
        summarizer = Agent(
            role="邮件摘要助手",
            goal="快速准确地提取邮件关键信息",
            backstory="""你是一个专业的邮件处理助手，负责对收到的邮件进行摘要。
            你擅长提取关键信息、识别重要事项，并能判断邮件的紧急程度。
            你的输出简洁明了，便于快速阅读。""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        task_summarize = Task(
            description=f"""分析以下邮件内容，生成简洁摘要：

邮件主题：{subject}

邮件正文：
{content}

要求：
1. 提取关键信息（会议、任务、截止日期等）
2. 摘要控制在 100 字以内
3. 判断重要性：高/中/低
4. 提取待办事项列表（如有）
5. 如果是纯广告/垃圾邮件，返回 null

输出 JSON 格式：
{{
  "summary": "邮件摘要",
  "importance": "high/medium/low",
  "action_items": ["待办1", "待办2"]
}}

注意：只输出 JSON，不要其他内容。""",
            agent=summarizer,
            expected_output="JSON 格式的邮件摘要"
        )

        crew = Crew(
            agents=[summarizer],
            tasks=[task_summarize],
            process=Process.sequential,
            verbose=False
        )

        logger.info(f"[EmailSummaryCrew] 开始生成摘要: {subject[:30]}...")
        result = crew.kickoff()
        logger.info(f"[EmailSummaryCrew] 摘要生成完成: {result}")

        return self._parse_result(result)

    def _parse_result(self, result) -> Optional[EmailSummary]:
        """解析 Crew 输出为 EmailSummary"""
        try:
            text = str(result)
            # 清理可能的 markdown 代码块
            cleaned = re.sub(r'```json?\n?', '', text)
            cleaned = re.sub(r'```\n?', '', cleaned)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            # 检查是否是垃圾邮件
            if data is None:
                return None

            # 如果 action_items 不是列表，尝试解析
            action_items = data.get("action_items", [])
            if isinstance(action_items, str):
                try:
                    action_items = json.loads(action_items)
                except:
                    action_items = [action_items]

            return EmailSummary(
                summary=data.get("summary", ""),
                importance=data.get("importance", "medium"),
                action_items=action_items
            )

        except json.JSONDecodeError as e:
            logger.error(f"[EmailSummaryCrew] JSON 解析失败: {e}, raw: {result}")
            return EmailSummary(
                summary=str(result)[:100],
                importance="medium",
                action_items=[]
            )
        except Exception as e:
            logger.error(f"[EmailSummaryCrew] 解析异常: {e}", exc_info=True)
            return EmailSummary(
                summary=str(result)[:100],
                importance="medium",
                action_items=[]
            )


def generate_email_summary(subject: str, content: str) -> Optional[EmailSummary]:
    """
    便捷函数：生成邮件摘要

    Args:
        subject: 邮件主题
        content: 邮件正文

    Returns:
        EmailSummary 或 None
    """
    crew = EmailSummaryCrew()
    return crew.run(subject, content)
