"""
新闻播报 Agent - 工具函数
"""
import requests
import json
import logging
from ..base.config import Config

logger = logging.getLogger(__name__)

def search_internet_tool(query: str) -> str:
    """Useful to search the internet for news, facts, and events. Returns search results."""
    if not Config.SERPER_API_KEY:
        return "Error: SERPER_API_KEY is not configured."

    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': Config.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        results = response.json()

        organic = results.get("organic", [])
        output = []
        for item in organic[:5]:
            output.append(f"Title: {item.get('title')}\nLink: {item.get('link')}\nSnippet: {item.get('snippet')}\n---")

        return "\n".join(output) if output else "No results found."
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error performing search: {e}"
