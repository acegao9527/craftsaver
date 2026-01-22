"""
文本处理 Crew
用于判断纯文本消息是"问答类"还是"记录类"
"""
import os
import re
import json
import logging
from typing import Dict, Any
from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool
from ..base.config import Config
from src.services.weather import get_city_weather, check_weather_query

logger = logging.getLogger(__name__)


# 独立函数工具（避免类方法的 self 传递问题）
@tool
def get_weather(city: str) -> str:
    """
    获取城市实时天气信息

    Args:
        city: 城市名称（支持：上海、北京、深圳、广州、杭州、南京、成都、武汉、重庆、西安）

    Returns:
        格式化的天气信息
    """
    return get_city_weather(city)


@tool
def weather_query_check(message: str) -> str:
    """
    检查消息是否在询问天气，并提取城市名

    Args:
        message: 用户消息

    Returns:
        JSON 格式：{"is_weather": true/false, "city": "城市名或null"}
    """
    return check_weather_query(message)


class TextAgentCrew:
    """文本处理 Crew"""

    def __init__(self):
        # 完全复用新闻播报的 LLM 配置
        self.llm = LLM(
            model=Config.OPENAI_MODEL_NAME,
            base_url=Config.OPENAI_API_BASE,
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3
        )

    def run(self, user_message: str) -> Dict[str, Any]:
        """
        执行文本分类

        Args:
            user_message: 用户发送的原始文本

        Returns:
            Dict: 包含 answer, reason, reply, summary 的结果
        """
        classifier = Agent(
            role="文本分类助手",
            goal="准确判断用户消息是问答类还是记录类，并给出相应输出",
            backstory="""你是一个智能助手，负责分析用户消息的意图。
            如果是问答类消息，准备给出有用的回答。
            如果是记录类消息，生成一个简洁的标题用于保存。
            你还可以调用天气工具回答天气相关问题。""",
            llm=self.llm,
            tools=[weather_query_check, get_weather],
            verbose=True,
            allow_delegation=False
        )

        task_classify = Task(
            description=f"""分析以下用户消息，判断是问答类还是记录类：

用户消息：{user_message}

## 特殊处理：天气查询

如果消息询问天气（包含"天气"、"温度"、"下雨"等关键词），执行以下步骤：
1. 首先调用 weather_query_check 工具检查是否天气查询
2. 如果是天气查询，调用 get_weather 工具获取天气
3. 在 reply 中返回天气信息

## 判断规则

### 问答类 (answer=true)
用户发送的是：
- 明确的提问（包含疑问词或问号）
- 需要解释或说明的内容
- 寻求帮助或建议
- **天气查询** ← 新增
- 示例：
  - "今天天气怎么样？"
  - "如何安装 Python？"
  - "帮我查一下 xxx"
  - "你知道 xxx 吗"
  - "上海天气"

### 记录类 (answer=false)
用户发送的是：
- 事实陈述
- 通知/公告
- 工作记录
- 备忘/清单
- 不包含疑问的纯文本
- 短文摘抄
- 示例：
  - "今天完成了需求评审"
  - "项目周一上线"
  - "开会时间改到下午3点"

## 输出要求
以 JSON 格式输出判断结果：
{{
  "answer": true 或 false,
  "reason": "简短判断理由（10字以内）",
  "reply": "如果是问答类，这里放回复内容；否则为 null",
  "summary": "如果是记录类，这里放保存用的摘要标题（15字以内）；否则为 null"
}}

规则：
- 问答类：包含疑问词(怎么/如何/什么/为什么/请问/能否)或问号，或**是天气查询**
- 记录类：纯陈述句，不包含上述特征
- 长度超过 500 字符自动判定为记录类
- 天气查询必须先调用工具获取信息，再回复用户
""",
            agent=classifier,
            expected_output="JSON 格式的分类结果，包含 answer/reply/summary 字段"
        )

        crew = Crew(
            agents=[classifier],
            tasks=[task_classify],
            process=Process.sequential,
            verbose=True
        )

        logger.info(f"[TextAgentCrew] 开始分析消息: {user_message[:50]}...")
        result = crew.kickoff()
        logger.info(f"[TextAgentCrew] 分析完成: {result}")

        # 解析 JSON 结果
        return self._parse_result(result)

    def _parse_result(self, result) -> Dict[str, Any]:
        """解析 Crew 输出为 JSON"""
        try:
            text = str(result)
            # 清理可能的 markdown 代码块
            cleaned = re.sub(r'```json?\n?', '', text)
            cleaned = re.sub(r'```\n?', '', cleaned)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            # 确保必要字段存在
            return {
                "answer": data.get("answer", False),
                "reason": data.get("reason", "默认记录"),
                "reply": data.get("reply"),
                "summary": data.get("summary")
            }

        except json.JSONDecodeError as e:
            logger.error(f"[TextAgentCrew] JSON 解析失败: {e}, raw: {result}")
            # 降级为记录类
            text = str(result)
            return {
                "answer": False,
                "reason": "解析失败降级",
                "reply": None,
                "summary": text[:50] + "..." if len(text) > 50 else text
            }
        except Exception as e:
            logger.error(f"[TextAgentCrew] 解析异常: {e}", exc_info=True)
            return {
                "answer": False,
                "reason": "异常降级",
                "reply": None,
                "summary": None
            }


def run_text_classification(message: str) -> Dict[str, Any]:
    """
    顶层函数：运行文本分类

    Args:
        message: 用户消息

    Returns:
        Dict: 分类结果
    """
    crew = TextAgentCrew()
    return crew.run(message)
