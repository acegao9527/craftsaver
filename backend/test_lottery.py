import logging
import asyncio
import os
from src.services.database import init_db
from src.agents.lottery import get_lottery_crew
from dotenv import load_dotenv

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init DB
init_db(os.getenv("SQLITE_DB_PATH", "data/savehelper.db"))

def check_env():
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_API_BASE")
    url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL_NAME")
    logger.info(f"Key: {key[:5]}...{key[-4:] if key else ''}")
    logger.info(f"Base: {base}")
    logger.info(f"URL: {url}")
    logger.info(f"Model: {model}")

async def test_crew():
    check_env()
    logger.info("Starting Lottery Crew Test...")
    crew = get_lottery_crew()
    result = await asyncio.to_thread(crew.kickoff)
    logger.info(f"Crew Result:\n{result}")

if __name__ == "__main__":
    asyncio.run(test_crew())