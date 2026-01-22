"""
天气服务
使用 Open-Meteo API（免费，无需 API Key）
"""
import logging
import re
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

# Open-Meteo API
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

# 城市坐标映射
CITY_COORDS = {
    "上海": {"lat": 31.2304, "lon": 121.4737},
    "北京": {"lat": 39.9042, "lon": 116.4074},
    "深圳": {"lat": 22.5431, "lon": 114.0579},
    "广州": {"lat": 23.1291, "lon": 113.2644},
    "杭州": {"lat": 30.2741, "lon": 120.1551},
    "南京": {"lat": 32.0603, "lon": 118.7969},
    "成都": {"lat": 30.5728, "lon": 104.0668},
    "武汉": {"lat": 30.5928, "lon": 114.3055},
    "重庆": {"lat": 29.5630, "lon": 106.5516},
    "西安": {"lat": 34.3416, "lon": 108.9398},
}


def get_city_weather(city: str) -> str:
    """
    获取城市实时天气信息

    Args:
        city: 城市名称，未指定时默认上海

    Returns:
        格式化的天气信息
    """
    if not city or city.strip() == "":
        city = "上海"
    weather = _fetch_weather(city)
    return _format_weather_reply(weather)


def check_weather_query(message: str) -> str:
    """
    检查消息是否在询问天气，并提取城市名

    Args:
        message: 用户消息

    Returns:
        JSON 格式：{"is_weather": true/false, "city": "城市名或null"}
    """
    city = extract_city_from_message(message)

    # 检查是否包含常见天气疑问词
    weather_keywords = ["天气", "温度", "下雨", "晴天", "冷", "热"]
    has_weather_keyword = any(kw in message for kw in weather_keywords)

    is_weather = has_weather_keyword

    # 如果是天气查询但没有明确城市，默认返回上海
    if is_weather and not city:
        city = "上海"

    import json
    return json.dumps({
        "is_weather": is_weather,
        "city": city
    }, ensure_ascii=False)


def _fetch_weather(city: str) -> Optional[Dict[str, Any]]:
    """获取城市天气数据"""
    # 尝试匹配城市
    city_key = city.strip()
    if city_key not in CITY_COORDS:
        for known_city in CITY_COORDS:
            if known_city in city_key or city_key in known_city:
                city_key = known_city
                break
        else:
            logger.warning(f"[Weather] 不支持的城市: {city}")
            return None

    coords = CITY_COORDS[city_key]
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Shanghai",
        "forecast_days": 1
    }

    try:
        logger.info(f"[Weather] 获取 {city} 天气...")
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return _parse_weather_data(data, city)
    except Exception as e:
        logger.error(f"[Weather] 获取失败: {e}")
        return None


def _parse_weather_data(data: dict, city: str) -> Dict[str, Any]:
    """解析 Open-Meteo 返回的数据"""
    current = data.get("current", {})
    daily = data.get("daily", {})
    units = data.get("current_units", {})

    weather_code = current.get("weather_code", 0)
    weather_desc = _get_weather_description(weather_code)

    temp = current.get("temperature_2m", "N/A")
    unit = units.get("temperature_2m", "°C")

    humidity = current.get("relative_humidity_2m", "N/A")
    humidity_unit = units.get("relative_humidity_2m", "%")

    if daily.get("temperature_2m_max") and daily.get("temperature_2m_min"):
        temp_max = daily["temperature_2m_max"][0]
        temp_min = daily["temperature_2m_min"][0]
        today_range = f"{temp_min}{unit} ~ {temp_max}{unit}"
    else:
        today_range = "N/A"

    return {
        "city": city,
        "temperature": f"{temp}{unit}",
        "humidity": f"{humidity}{humidity_unit}",
        "weather": weather_desc,
        "today_range": today_range,
    }


def _get_weather_description(code: int) -> str:
    """天气代码转中文描述"""
    weather_map = {
        0: "晴朗", 1: "基本晴朗", 2: "多云", 3: "阴天",
        45: "雾", 48: "雾凇", 51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
        80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        95: "雷暴", 96: "雷暴+小冰雹", 99: "雷暴+大冰雹",
    }
    return weather_map.get(code, f"未知({code})")


def _format_weather_reply(weather: Optional[Dict]) -> str:
    """格式化天气回复"""
    if not weather:
        return "抱歉，暂时无法获取天气信息"

    city = weather.get("city", "")
    temp = weather.get("temperature", "N/A")
    humidity = weather.get("humidity", "N/A")
    weather_desc = weather.get("weather", "N/A")
    today_range = weather.get("today_range", "N/A")

    return f"【{city}今日天气】\n\n🌡️ 温度: {temp}\n💧 湿度: {humidity}\n🌤️ 天气: {weather_desc}\n📈 今日: {today_range}"


def extract_city_from_message(message: str) -> Optional[str]:
    """从消息中提取城市名"""
    for known in CITY_COORDS:
        if known in message:
            return known
    return None
