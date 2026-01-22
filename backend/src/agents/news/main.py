"""
新闻播报 Agent 主入口
"""
import sys
import logging
from .config import Config
from .crew import NewsCrew

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Kindergarten News Crew...")

    try:
        # 1. Validate Configuration
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"Configuration Error: {e}")
            logger.info("Please set the required environment variables in your .env file.")
            sys.exit(1)

        # 2. Run CrewAI to generate script
        logger.info("Kicking off CrewAI agents...")
        news_crew = NewsCrew()
        script_result = news_crew.run()

        if not script_result:
            logger.error("CrewAI returned empty result.")
            sys.exit(1)

        logger.info("Script generated successfully!")
        print("\n--- Generated Script ---\n")
        print(script_result)
        print("\n------------------------\n")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
