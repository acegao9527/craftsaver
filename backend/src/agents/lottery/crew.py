"""
抽奖 Agent (CrewAI)
"""
import re
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import logging
from ..base.config import Config
from .tools import TodayParticipantsTool

logger = logging.getLogger(__name__)

def get_lottery_crew():
    """创建抽奖 Crew"""
    # 1. 初始化 LLM
    llm = ChatOpenAI(
        model=Config.OPENAI_MODEL_NAME,
        base_url=Config.OPENAI_API_BASE,
        api_key=Config.OPENAI_API_KEY
    )

    # 2. 创建 Agent
    registrar = Agent(
        role="报名登记员",
        goal="获取并清洗今天所有报名抽奖的人员名单",
        backstory="你是一位细心的登记员，负责核对抽奖报名名单。你需要确保名单准确无误，并去除重复和不合规的报名。",
        verbose=True,
        llm=llm,
        tools=[TodayParticipantsTool()],
        allow_delegation=False
    )

    drawer = Agent(
        role="抽奖主持人",
        goal="从清洗后的名单中随机抽取2位中奖者",
        backstory="你是一位专业的抽奖主持人，负责公平公正地抽取中奖者。你的任务是随机选择2位幸运儿。",
        verbose=True,
        llm=llm,
        allow_delegation=False
    )

    auditor = Agent(
        role="抽奖审计员",
        goal="确认中奖名单并发布最终公告",
        backstory="你是一位严谨的审计员，负责确认抽奖结果的合规性和发布最终的中奖公告。",
        verbose=True,
        llm=llm,
        allow_delegation=False
    )

    # 定义任务 - 移除 output_pydantic，改用文本传递，依靠 Prompt 和最终清洗
    task_clean = Task(
        description="""
        使用 TodayParticipantsTool 获取今天的报名名单。
        注意：你只能处理今天（当前日期）报名的名单，工具已经为你过滤了日期，你只需确保数据清洗无误。
        去除重复项，移除不合规的名字（非中文名）。

        **输出格式要求：**
        请输出一个 JSON 格式的字符串，包含清洗后的名单。
        示例：
        {"names": ["张三", "李四"]}
        """,
        expected_output='清洗后的候选人名单 JSON 字符串',
        agent=registrar
    )

    task_draw = Task(
        description="""
        基于上一位 Agent 提供的 JSON 名单，随机挑选 2 位中奖者。

        **输出格式要求：**
        请输出一个 JSON 格式的字符串，包含 2 位中奖者。
        示例：
        {"winners": ["张三", "李四"]}
        """,
        expected_output='2位中奖者的名字 JSON 字符串',
        agent=drawer
    )

    task_audit = Task(
        description="""
        基于上一位 Agent 提供的 JSON 中奖名单，确认名单为 2 位中文名中奖者。
        输出一段格式优美的中奖公告。两名中奖者都是来自应用开发二室，真诚的祝福这两位正直聪明的同事。

        **输出格式要求：**
        1. 仅输出最终的纯文本公告。
        2. 不要包含 JSON 结构。
        """,
        expected_output='最终的中奖公告文本',
        agent=auditor
    )

    # 组建 Crew
    crew = Crew(
        agents=[registrar, drawer, auditor],
        tasks=[task_clean, task_draw, task_audit],
        process=Process.sequential,
        verbose=True
    )

    return crew

def run_lottery_crew() -> str:
    """
    运行抽奖 Crew 并清洗输出
    """
    try:
        crew = get_lottery_crew()
        result = crew.kickoff()

        # 转换为字符串
        final_str = str(result)

        # 兜底清理：如果审计员还是忍不住输出了 thinking 标签
        logger.info("[LotteryCrew] 最终输出内容兜底清理...")
        cleaned_result = re.sub(r'<thinking>.*?</thinking>', '', final_str, flags=re.DOTALL | re.IGNORECASE)
        cleaned_result = re.sub(r'^Thought:.*$', '', cleaned_result, flags=re.MULTILINE)
        cleaned_result = re.sub(r'^Action:.*$', '', cleaned_result, flags=re.MULTILINE)
        cleaned_result = cleaned_result.strip()

        return cleaned_result
    except Exception as e:
        logger.error(f"[LotteryCrew] Execution failed: {e}", exc_info=True)
        return f"抽奖过程发生错误: {str(e)}"
