"""
共享的 Agent 配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # OpenAI / LLM
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")

    # Serper for Google Search
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
