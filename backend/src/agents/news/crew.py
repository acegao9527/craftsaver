"""
幼儿园新闻播报 Agent (CrewAI)
"""
import re
import os
from typing import List
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew, CrewOutput, Process

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)


class NewsCrew:
    def __init__(self):
        # 1. 创建 Agent
        logger.info("[NewsCrew] 创建 Agent...")
        researcher = Agent(
            role="News Researcher",
            goal="Research today's news events suitable for kindergarten children",
            backstory="You are a news researcher specialized in finding child-friendly news. You search for positive, educational, and interesting news for kindergarten children.",
            verbose=True,
            allow_delegation=False
        )
        writer = Agent(
            role="News Writer",
            goal="Write a lively news script for kindergarten children",
            backstory="You are a creative news writer who writes engaging and age-appropriate news scripts for kindergarten children. Your writing is lively, simple, and fun.",
            verbose=True,
            allow_delegation=False
        )
        reviewer = Agent(
            role="News Reviewer",
            goal="Review and clean up the news script",
            backstory="You are a meticulous reviewer who ensures the news script is perfect for kindergarten children. You remove any inappropriate content and ensure the language is age-appropriate.",
            verbose=True,
            allow_delegation=False
        )

        self.researcher = researcher
        self.writer = writer
        self.reviewer = reviewer

    def run(self) -> str:
        # 2. 定义 Task
        logger.info("[NewsCrew] 定义 Task...")

        today = datetime.now().strftime("%Y年%m月%d日")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y年%m月%d日")

        task_search = Task(
            description=f"""Research today's news for kindergarten children.

**Your goal:** Find 2-3 positive, educational news stories suitable for kindergarten children aged 3-6.

**Requirements:**
1. Search for news about: {today} or {tomorrow}
2. Look for: cute animals, science discoveries, art activities, sports events, environmental protection, or other child-friendly topics.
3. Avoid: violence, disasters, politics, or scary content.

**Output:**
Return a brief summary of each news item (2-3 items) with:
- Title
- A 2-3 sentence child-friendly description
- Source or date reference
""",
            agent=self.researcher,
            expected_output="A list of 2-3 child-friendly news stories with brief descriptions."
        )

        task_write = Task(
            description=f"""Write a news broadcast script for kindergarten children.

**Context:**
{task_search.output}

**Your requirements:**
1. Create a lively, engaging news script that a teacher can read to kindergarten children.
2. Write in Chinese (Simplified).
3. Start with: "小朋友们好！今天是{today}..." (Today's date in Chinese)
4. Cover each news item in 1-2 sentences.
5. **只写一条新闻**。
6. 全文是一个**连贯的段落**，不要分段，不要回车换行。
7. 字数严格控制在**80字左右**。
8. 语气活泼，适合幼儿园小朋友听。

**期望的输出格式示例：**
小朋友们好！今天告诉大家一个好消息，我们的熊猫宝宝长大了...（接具体新闻）...真是太棒了！今天的播报就到这里，我们明天见！
""",
            agent=self.writer,
            expected_output="一段约80字的纯文本新闻播报稿草稿。"
        )

        task_review = Task(
            description="""审查并最终定稿新闻播报稿。

            **你的最高职责是清洗数据：**
            1. **删除所有 <think>...</think> 标签及其内部的思考过程。** 这是最关键的。
            2. 删除所有 "Thought:", "Action:", "Observation:" 等 ReAct 格式残留。
            3. 删除所有 "好的"、"以下是播报稿"、"Here is the script" 等对话废话。
            4. 删除所有 Markdown 格式（**粗体**、标题等）。
            5. 确保剩下的内容是**唯一的一段**连贯的播报词。

            如果发现任何上述垃圾内容，**必须**将其全部删除，只保留那一段纯净的新闻稿。
            如果稿件不合格，请重新改写为一段约80字的纯文本口播稿。

            **最终输出示例（绝对标准）：**
            小朋友们好！听说2025年11月在上海举办了一个超酷的儿童绘画展，好多小朋友都画出了自己心目中的未来城市，真是太有创意啦！我们也要像他们一样大胆想象哦。今天的播报就到这里，明天见！
            """,
            agent=self.reviewer,
            expected_output="最终的、纯净的、无格式的新闻播报稿文本。"
        )

        # Crew 组织
        logger.info("[NewsCrew] 组装 Crew...")
        crew = Crew(
            agents=[self.researcher, self.writer, self.reviewer],
            tasks=[task_search, task_write, task_review],
            process=Process.sequential,
            verbose=True
        )

        logger.info("[NewsCrew] 🚀 启动 Crew (crew.kickoff)... 这可能需要几分钟...")
        result = crew.kickoff()
        logger.info("[NewsCrew] Crew 执行完成!")
        return result

def run_news_crew() -> str:
    """
    顶层函数：初始化并运行 NewsCrew。
    设计用于在独立进程中运行。
    """
    logger.info("[NewsCrew] 进入 run_news_crew 函数")
    try:
        crew = NewsCrew()
        result = str(crew.run())

        # 强制清理 <think> 标签及其内容
        logger.info("[NewsCrew] 清理输出内容 (thinking 标签)...")
        # 1. Remove thinking blocks
        cleaned_result = re.sub(r'<thinking>.*?</thinking>', '', result, flags=re.DOTALL | re.IGNORECASE)
        # 2. Remove "Thought: ..." lines if any remain
        cleaned_result = re.sub(r'^Thought:.*$', '', cleaned_result, flags=re.MULTILINE)
        # 3. Remove "Action: ..." lines
        cleaned_result = re.sub(r'^Action:.*$', '', cleaned_result, flags=re.MULTILINE)
        # 4. Remove empty lines and trim
        cleaned_result = cleaned_result.strip()

        logger.info(f"[NewsCrew] 处理完成，结果长度: {len(cleaned_result)}")
        return cleaned_result
    except Exception as e:
        logger.error(f"[NewsCrew] 执行过程中发生未捕获异常: {e}", exc_info=True)
        raise
