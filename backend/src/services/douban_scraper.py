"""豆瓣电影观看记录爬虫服务"""
import os
import re
import sqlite3
import sys
import httpx
import logging
import random
from lxml import html
from typing import List, Optional, Dict, Any
from datetime import datetime

sys.path.insert(0, "/app")
from src.models.douban import DoubanMovie

logger = logging.getLogger(__name__)


class DoubanScraper:
    """豆瓣爬虫"""

    # 列表类型配置
    LIST_TYPES = {
        "collect": "看过",
        "wish": "想看",
        "doing": "在看",
    }

    def __init__(self):
        self.user_id = os.getenv("DOUBAN_USER_ID", "")
        self.cookie = os.getenv("DOUBAN_COOKIE", "")
        self.base_url = "https://movie.douban.com"

        # 代理配置
        self.proxy_enabled = os.getenv("DOUBAN_PROXY_ENABLED", "").lower() == "true"
        # 支持多种代理格式：
        # 1. 代理池 API URL: DOUBAN_PROXY_URL=http://proxy.example.com/api
        # 2. 单个代理: DOUBAN_PROXY_URL=http://user:pass@ip:port
        self.proxy_url = os.getenv("DOUBAN_PROXY_URL", "")
        self.proxy_list = []

        # 多种 User-Agent 轮换，模拟不同浏览器
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        ]

        self.headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cookie": self.cookie,
        }
        self.db_path = os.getenv("SQLITE_DB_PATH", "data/savehelper.db")

    def get_proxy(self) -> Optional[str]:
        """从代理池获取一个代理"""
        if not self.proxy_enabled:
            return None

        # 如果配置了代理列表，随机选择一个
        if self.proxy_list:
            return random.choice(self.proxy_list)

        # 如果配置了代理 API，从 API 获取
        if self.proxy_url:
            try:
                # 判断是 API URL 还是单个代理
                if "://" in self.proxy_url and not self.proxy_url.startswith("http://") and not self.proxy_url.startswith("https://"):
                    # 看起来是单个代理地址
                    return self.proxy_url

                # 调用代理 API
                response = httpx.get(self.proxy_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # 常见的代理 API 格式
                    if isinstance(data, list) and data:
                        proxy = data[0].get("proxy", data[0].get("ip", ""))
                        if proxy:
                            self.proxy_list.append(f"http://{proxy}")
                            return self.proxy_list[-1]
                    elif isinstance(data, dict):
                        proxy = data.get("proxy", data.get("data", {}).get("proxy", ""))
                        if proxy:
                            return f"http://{proxy}"
            except Exception as e:
                logger.warning(f"获取代理失败: {e}")

        return None

    def build_proxy_dict(self, proxy: str) -> dict:
        """将代理字符串转换为 httpx 需要的格式"""
        if not proxy:
            return {}
        return {
            "http://": proxy,
            "https://": proxy,
        }

    def refresh_headers(self):
        """定期刷新请求头，模拟不同的浏览器会话"""
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        ]

        # 随机化 Accept-Language
        languages = [
            "zh-CN,zh;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "zh-TW,zh;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.8,zh-TW;q=0.7,en;q=0.5",
        ]

        self.headers["User-Agent"] = random.choice(user_agents)
        self.headers["Accept-Language"] = random.choice(languages)

        # 随机化 Referer（模拟从不同页面进入）
        referers = [
            "https://movie.douban.com/",
            "https://movie.douban.com/mine?from=subject-overview",
            "https://www.douban.com/",
        ]
        self.headers["Referer"] = random.choice(referers)

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return sqlite3.connect(self.db_path)

    def parse_rating_star(self, rating_str: str) -> Optional[float]:
        """解析评分星级为数字"""
        if not rating_str:
            return None
        # 评分可能是 "rating-stars-45" 或 "rating4-t" 等格式
        match = re.search(r"(\d+)", rating_str)
        if match:
            val = int(match.group(1))
            if val > 10:  # 如 45 表示 4.5星
                return val / 10
            else:
                return val / 2  # 如 4 表示 2星
        return None

    def parse_year(self, year_str: str) -> Optional[int]:
        """解析年份"""
        if not year_str:
            return None
        match = re.search(r"(\d{4})", year_str)
        if match:
            return int(match.group(1))
        return None

    async def async_fetch(self, url: str, headers: dict) -> httpx.Response:
        """异步获取页面（支持代理）"""
        proxy = self.get_proxy()
        proxies = self.build_proxy_dict(proxy) if proxy else {}

        async with httpx.AsyncClient(timeout=15, proxies=proxies) as client:
            return await client.get(url, headers=headers)

    # 简繁转换映射表（完整版）
    TRADITIONAL_TO_SIMPLIFIED = {
        # 常见繁体字 - 补充完整
        "為": "为", "於": "于", "與": "与", "對": "对", "從": "从",
        "會": "会", "說": "说", "時": "时", "長": "长", "東": "东",
        "來": "来", "這": "这", "國": "国", "家": "家", "裡": "里",
        "後": "后", "過": "过", "還": "还", "機": "机", "發": "发",
        "關": "关", "無": "无", "義": "义", "醫": "医", "爾": "尔",
        "隻": "只", "讓": "让", "們": "们", "種": "种", "愛": "爱",
        "學": "学", "氣": "气", "號": "号", "聽": "听", "請": "请",
        "話": "话", "該": "该", "間": "间", "題": "题", "門": "门",
        "車": "车", "幾": "几", "點": "点", "農": "农", "烏": "乌",
        "風": "风", "鳥": "鸟", "龍": "龙", "龜": "龟", "齊": "齐",
        "齒": "齿", "萬": "万", "歲": "岁", "電": "电", "雲": "云",
        "藝": "艺", "殺": "杀", "藥": "药", "樂": "乐", "參": "参",
        "產": "产", "節": "节", "覺": "觉", "樓": "楼", "筆": "笔",
        "談": "谈", "試": "试", "語": "语", "記": "记", "認": "认",
        "誤": "误", "訴": "诉", "謝": "谢", "際": "际", "難": "难",
        "靜": "静", "順": "顺", "願": "愿", "優": "优", "導": "导",
        "敵": "敌", "戰": "战", "黨": "党", "內": "内", "兩": "两",
        "滿": "满", "網": "网", "組": "组", "統": "统", "營": "营",
        "轉": "转", "專": "专", "場": "场", "塊": "块", "報": "报",
        "夠": "够", "線": "线", "縣": "县", "濟": "济", "帶": "带",
        "處": "处", "標": "标", "權": "权", "親": "亲", "餘": "余",
        "療": "疗", "獲": "获", "護": "护", "贊": "赞", "極": "极",
        "棄": "弃", "喪": "丧", "協": "协", "壓": "压", "躍": "跃",
        "麗": "丽", "幫": "帮", "啟": "启", "評": "评", "畫": "画",
        "聯": "联", "聲": "声", "環": "环", "備": "备", "複": "复",
        "製": "制", "質": "质", "興": "兴", "舊": "旧", "藍": "蓝",
        "觀": "观", "讀": "读", "論": "论", "贏": "赢", "趕": "赶",
        "湯": "汤", "溝": "沟", "穩": "稳", "滅": "灭", "廳": "厅",
        "濱": "滨", "濾": "滤", "爺": "爷", "孫": "孙", "戲": "戏",
        "員": "员", "寶": "宝", "島": "岛", "峽": "峡", "庫": "库",
        "應": "应", "彈": "弹", "彩": "彩", "獎": "奖", "奪": "夺",
        "宮": "宫", "寵": "宠", "廟": "庙", "廠": "厂", "廢": "废",
        "彌": "弥", "幣": "币", "徑": "径", "憲": "宪", "憶": "忆",
        "憂": "忧", "擁": "拥", "擇": "择", "擺": "摆", "擊": "击",
        "擔": "担", "擬": "拟", "攝": "摄", "擴": "扩", "敗": "败",
        "陸": "陆", "險": "险", "陽": "阳", "階": "阶", "隊": "队",
        "除": "除", "陳": "陈", "陰": "阴", "隨": "随", "齡": "龄",
        "鐘": "钟", "鐵": "铁", "鋼": "钢", "銀": "银", "銅": "铜",
        "鋁": "铝", "鍋": "锅", "錯": "错", "錄": "录", "鍾": "钟",
        "鉛": "铅", "針": "针", "鐮": "镰", "鏟": "铲", "鍛": "锻",
        "銷": "销", "鎖": "锁", "鎚": "锤", "鏈": "链", "鏡": "镜",
        "鐺": "铛", "鏢": "镖", "錦": "锦", "鍵": "键", "鎮": "镇",
        "鎬": "镐", "鎳": "镍", "鎰": "镒", "鎦": "镏", "鏗": "铿",
        "鏃": "簇", "鏤": "镂", "鐃": "铙", "鐲": "镯", "鐮": "镰",
        "鑄": "铸", "鑒": "鉴", "鑠": "铄", "鑿": "凿", "鑼": "锣",
        "鑽": "钻", "鑰": "钥", "龜": "龟", "鹵": "卤", "鹽": "盐",
        "鹹": "咸", "麥": "麦", "黃": "黄", "黽": "黾", "鼎": "鼎",
        "鼓": "鼓", "鼠": "鼠", "將": "将", "漿": "浆", "獎": "奖",
        "狀": "状", "莊": "庄", "煙": "烟", "婁": "娄", "樓": "楼",
        "淚": "泪", "類": "类", "繼": "继", "繩": "绳", "繞": "绕",
        "繪": "绘", "繡": "绣", "維": "维", "綁": "绑", "縱": "纵",
        "織": "织", "繳": "缴", "繹": "绎", "綢": "绸", "綠": "绿",
        "緊": "紧", "總": "总", "績": "绩", "緒": "绪", "綾": "绫",
        "繖": "伞", "緬": "缅", "纖": "纤", "纜": "缆", "縫": "缝",
        "纏": "缠", "罐": "罐", "罕": "罕", "羔": "羔", "羣": "群",
        "習": "习", "翹": "翘", "耙": "耙", "耕": "耕", "聯": "联",
        "聖": "圣", "聰": "聪", "聶": "聂", "職": "职", "聾": "聋",
        "肅": "肃", "腸": "肠", "腫": "肿", "腦": "脑", "膽": "胆",
        "臉": "脸", "臘": "腊", "臥": "卧", "舘": "馆", "艙": "舱",
        "艷": "艳", "莖": "茎", "螞": "蚂", "蠱": "蛊", "螢": "萤",
        "螳": "螳", "螺": "螺", "蟻": "蚁", "蠶": "蚕", "蠅": "蝇",
        "蠍": "蝎", "蠟": "蜡", "襯": "衬", "襲": "袭", "襪": "袜",
        "褲": "裤", "見": "见", "規": "规", "視": "视", "覽": "览",
        "觸": "触", "訃": "讣", "診": "诊", "詐": "诈", "詔": "诏",
        "詞": "词", "譜": "谱", "警": "警", "譯": "译", "議": "议",
        "謙": "谦", "講": "讲", "謀": "谋", "謊": "谎", "謎": "谜",
        "謬": "谬", "譽": "誉", "認": "认", "誦": "诵", "誨": "诲",
        "誑": "诓", "誥": "诰", "諱": "讳", "諂": "谄", "諍": "诤",
        "謂": "谓", "識": "识", "詩": "诗", "誠": "诚", "誕": "诞",
        "課": "课", "誹": "诽", "諦": "谛", "諷": "讽", "諸": "诸",
        "諾": "诺", "謀": "谋", "謊": "谎", "謎": "谜", "謹": "谨",
        "識": "识", "議": "议", "讓": "让", "豐": "丰", "豬": "猪",
        "敗": "败", "賤": "贱", "賜": "赐", "賴": "赖", "賺": "赚",
        "購": "购", "賽": "赛", "賁": "贲", "賢": "贤", "賣": "卖",
        "賤": "贱", "賺": "赚", "購": "购", "賽": "赛", "贅": "赘",
        "賦": "赋", "賢": "贤", "賤": "贱", "賞": "赏", "賜": "赐",
        "贏": "赢", "贊": "赞", "贛": "赣", "趨": "趋", "趙": "赵",
        "跡": "迹", "蹤": "踪", "踐": "践", "蹟": "迹", "蹣": "蹒",
        "蹶": "蹶", "蹈": "蹈", "蹊": "蹊", "蹶": "蹶", "蹦": "蹦",
        "蹤": "踪", "躉": "趸", "躍": "跃", "躊": "踌", "躇": "躇",
        "躋": "跻", "躍": "跃", "躑": "踯", "躓": "踬", "躊": "踌",
        "轎": "轿", "輕": "轻", "載": "载", "輛": "辆", "輝": "辉",
        "輟": "辍", "輻": "辐", "輯": "辑", "輸": "输", "輾": "碾",
        "轆": "辘", "轍": "辙", "轔": "辚", "轎": "轿", "轉": "转",
        "軸": "轴", "較": "较", "輒": "辄", "輓": "挽", "載": "载",
        "輔": "辅", "輛": "辆", "輩": "辈", "輪": "轮", "輟": "辍",
        "輸": "输", "輻": "辐", "輯": "辑", "轟": "轰", "轄": "辖",
        "輾": "碾", "轉": "转", "軸": "轴", "輕": "轻", "軟": "软",
        "車": "车", "軌": "轨", "軍": "军", "軒": "轩", "軟": "软",
        "轉": "转", "軸": "轴", "較": "较", "載": "载", "輕": "轻",
        "幣": "币", "師": "师", "帥": "帅", "幫": "帮", "帶": "带",
        "幀": "帧", "幃": "帏", "幗": "帼", "幔": "幔", "幕": "幕",
        "幟": "帜", "幣": "币", "幘": "帻", "幗": "帼", "幫": "帮",
        "幣": "币", "幘": "帻", "幗": "帼", "幫": "帮", "帶": "带",
        "幣": "币", "師": "师", "幀": "帧", "幃": "帏", "幗": "帼",
        "幔": "幔", "幕": "幕", "幟": "帜", "幘": "帻", "幣": "币",
        "幫": "帮", "帶": "带", "幘": "帻", "幗": "帼", "幫": "帮",
        "帶": "带", "幣": "币", "師": "师", "帥": "帅", "幫": "帮",
        "帶": "带", "幣": "币", "師": "师", "帥": "帅", "幫": "帮",
        "帶": "带", "幣": "币", "師": "师", "帥": "帅", "幫": "帮",
        "帶": "带", "幣": "币", "師": "师", "帥": "帅", "幫": "帮",
        # 更多常见繁体字
        "魚": "鱼", "魯": "鲁", "鮑": "鲍", "鯊": "鲨", "鯽": "鲫",
        "鮮": "鲜", "鯨": "鲸", "鯉": "鲤", "鯽": "鲫", "鯊": "鲨",
        "鰱": "鲢", "鱒": "鳟", "鱗": "鳞", "鱷": "鳄", "鱔": "鳝",
        "鱖": "鳜", "魷": "鱿", "魘": "魇", "魚": "鱼", "魯": "鲁",
        "錢": "钱", "銳": "锐", "鋼": "钢", "錐": "锥", "錄": "录",
        "墻": "墙", "墾": "垦", "壇": "坛", "壑": "壑", "壓": "压",
        "壞": "坏", "壩": "坝", "壯": "壮", "壺": "壶", "壽": "寿",
        "夢": "梦", "夾": "夹", "奧": "奥", "奪": "夺", "奮": "奋",
        "妝": "妆", "婦": "妇", "嬰": "婴", "嬌": "娇", "嬗": "嬗",
        "孫": "孙", "學": "学", "孿": "孪", "寧": "宁", "審": "审",
        "屆": "届", "層": "层", "屍": "尸", "屎": "屎", "屏": "屏",
        "屆": "届", "層": "层", "屬": "属", "嶺": "岭", "巖": "岩",
        "帥": "帅", "師": "师", "幀": "帧", "帶": "带", "幣": "币",
        "簾": "帘", "簷": "檐", "籃": "篮", "籌": "筹", "簽": "签",
        "籐": "藤", "籠": "笼", "籟": "籁", "籍": "籍", "籤": "签",
        "米": "米", "類": "类", "粟": "粟", "粵": "粤", "糧": "粮",
        "粹": "粹", "粽": "粽", "精": "精", "糊": "糊", "糰": "团",
        "糙": "糙", "糜": "糜", "糟": "糟", "糠": "糠", "糞": "粪",
        "糧": "粮", "糰": "团", "糙": "糙", "糜": "糜", "糟": "糟",
        "糧": "粮", "糯": "糯", "餅": "饼", "餌": "饵", "餓": "饿",
        "餒": "馁", "餘": "余", "餛": "馄", "餡": "馅", "館": "馆",
        "餽": "馈", "餾": "馏", "餿": "馊", "饅": "馒", "饑": "饥",
        "饞": "馋", "饅": "馒", "饑": "饥", "饋": "馈", "餾": "馏",
        "餿": "馊", "餾": "馏", "餿": "馊", "饅": "馒", "饑": "饥",
        "饞": "馋", "馬": "马", "馭": "驭", "駁": "驳", "駐": "驻",
        "駒": "驹", "駕": "驾", "駙": "驸", "駕": "驾", "駛": "驶",
        "駝": "驼", "駭": "骇", "駱": "骆", "驅": "驱", "驢": "驴",
        "驕": "骄", "驟": "骤", "驗": "验", "騰": "腾", "驚": "惊",
        "驗": "验", "騰": "腾", "驚": "惊", "驟": "骤", "驅": "驱",
        "驢": "驴", "驕": "骄", "驗": "验", "騰": "腾", "驚": "惊",
        "骯": "脏", "骰": "骰", "骯": "脏", "骶": "骶", "骸": "骸",
        "骼": "骼", "髏": "骷髅", "髖": "髋", "髓": "髓", "體": "体",
        "髖": "髋", "髓": "髓", "髏": "骷髅", "髪": "发", "鬆": "松",
        "鬧": "闹", "鬚": "须", "鬢": "鬓", "鬥": "斗", "鬧": "闹",
        "鬆": "松", "鬚": "须", "鬢": "鬓", "鬱": "郁", "魷": "鱿",
        "魘": "魇", "魯": "鲁", "鯊": "鲨", "鯽": "鲫", "鮮": "鲜",
        "鯨": "鲸", "鯉": "鲤", "鰱": "鲢", "鱒": "鳟", "鱗": "鳞",
        "鱷": "鳄", "鱔": "鳝", "鱖": "鳜", "鳥": "鸟", "鳳": "凤",
        "鳴": "鸣", "鴆": "鸩", "鴉": "鸦", "鴿": "鸽", "鴻": "鸿",
        "鵑": "鹃", "鵝": "鹅", "鵠": "鹄", "鵡": "鹉", "鵬": "鹏",
        "鵲": "鹊", "鵪": "鹌", "鵾": "鸱", "鶴": "鹤", "鸚": "鹦",
        "鸛": "鹳", "鹵": "卤", "鹽": "盐", "鹿": "鹿", "麂": "麂",
        "麝": "麝", "麟": "麟", "麗": "丽", "麥": "麦", "麩": "麸",
        "麵": "面", "麩": "麸", "麵": "面", "黃": "黄", "黍": "黍",
        "黏": "黏", "黛": "黛", "黜": "黜", "黝": "黝", "黠": "黠",
        "鼇": "鳌", "鼈": "鳖", "齊": "齐", "齒": "齿", "齡": "龄",
        "齣": "出", "齦": "龈", "齧": "啮", "齪": "龊", "齷": "龌",
        "龍": "龙", "龐": "庞", "龜": "龟", "龠": "龠", "侶": "侣",
        "侶": "侣", "僑": "侨", "僑": "侨", "僱": "雇", "僖": "嬉",
        "價": "价", "儀": "仪", "億": "亿", "儉": "俭", "儒": "儒",
        "儕": "侪", "儔": "俦", "儘": "尽", "優": "优", "儲": "储",
        "儡": "儡", "儲": "储", "優": "优", "償": "偿", "儡": "儡",
        "優": "优", "償": "偿", "優": "优", "儲": "储", "優": "优",
        # 补充缺失的繁体字
        "搶": "抢", "禱": "祷", "禍": "祸", "禿": "秃", "禪": "禅",
        "稟": "禀", "稱": "称", "穀": "谷", "穎": "颖", "窺": "窥",
        "竊": "窃", "籲": "吁", "纏": "缠", "聯": "联", "職": "职",
        "艱": "艰", "藝": "艺", "藍": "蓝", "蘭": "兰", "蘊": "蕴",
        "蟲": "虫", "蠟": "蜡", "衛": "卫", "裝": "装", "見": "见",
        "覺": "觉", "討": "讨", "誤差": "误差", "誘": "诱", "說": "说",
        "讀": "读", "變": "变", "讚": "赞", "豐": "丰", "貝": "贝",
        "賄": "贿", "賓": "宾", "賢": "贤", "賤": "贱", "賭": "赌",
        "購": "购", "賽": "赛", "贅": "赘", "贊": "赞", "趙": "赵",
        "踐": "践", "面積": "面积", "碼": "码", "輕": "轻", "辦": "办",
        "辭": "辞", "邊": "边", "遷": "迁", "選": "选", "遺": "遗",
        "郵": "邮", "鄉": "乡", "釋": "释", "針": "针", "釘": "钉",
        "鈕": "钮", "錢": "钱", "鋁": "铝", "銳": "锐", "錄": "录",
        "錐": "锥", "鋼": "钢", "鍋": "锅", "鍵": "键",
    }

    def fetch_movie_detail(self, douban_id: str) -> Optional[Dict[str, str]]:
        """获取电影详情页，尝试获取简体标题"""
        url = f"https://movie.douban.com/subject/{douban_id}/"

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=self.headers)
                if response.status_code != 200:
                    return None

                tree = html.fromstring(response.text)

                # 尝试多种方式获取中文标题

                # 1. 从 <span property="v:itemreviewed"> 获取（通常是中文标题）
                title_elem = tree.xpath('//span[@property="v:itemreviewed"]')
                if title_elem and title_elem[0].text:
                    return {"title": title_elem[0].text.strip()}

                # 2. 从 <h1> 标题区域获取
                h1_elem = tree.xpath('//h1')
                if h1_elem and h1_elem[0].text:
                    text = h1_elem[0].text_content().strip()
                    # 清理可能的年份信息
                    text = re.sub(r'\s*\(\d{4}\)\s*$', '', text)
                    return {"title": text}

                # 3. 从 <span class="title"> 获取（中文标题通常在第一个 title span）
                title_span = tree.xpath('//span[@class="title"]')
                if title_span and title_span[0].text:
                    return {"title": title_span[0].text.strip()}

                return None

        except Exception as e:
            logger.error(f"获取电影详情失败 {douban_id}: {e}")
            return None

    def _to_simplified(self, text: str) -> str:
        """繁体转简体"""
        if not text:
            return text
        result = text
        for trad, simp in self.TRADITIONAL_TO_SIMPLIFIED.items():
            result = result.replace(trad, simp)
        return result

    def _extract_chinese_title(self, title_raw: str) -> str:
        """
        从豆瓣 title 属性提取中文标题
        格式示例: "Arrival / 降临" 或 "悟空传 / Wukong Zhuan / ..."
        豆瓣格式：英文在前，中文在后，用 "/" 分隔
        """
        if not title_raw:
            return title_raw

        # 按 "/" 分割
        parts = [p.strip() for p in title_raw.split("/")]

        # 豆瓣通常格式：英文名 / 中文名 / 其他别名
        # 所以找最后一个包含中文的部分作为中文标题
        for part in reversed(parts):
            has_chinese = bool(re.search("[\u4e00-\u9fff]", part))
            if has_chinese:
                return self._to_simplified(part)

        # 如果没有中文，返回第一个部分
        return self._to_simplified(parts[0]) if parts else title_raw

    def _extract_original_title(self, title_raw: str) -> Optional[str]:
        """
        从豆瓣 title 属性提取原标题（英文或其他语言）
        格式示例: "Arrival / 降临"
        """
        if not title_raw:
            return None

        parts = [p.strip() for p in title_raw.split("/")]

        # 豆瓣格式：英文名 / 中文名
        # 第一部分通常是原标题（英文）
        if len(parts) >= 2:
            first_part = parts[0]
            has_chinese = bool(re.search("[\u4e00-\u9fff]", first_part))
            # 如果第一部分不包含中文，则是原标题
            if not has_chinese:
                return first_part
            # 如果第一部分是中文，则没有原标题
            return None

        return None

    def extract_movie_info(self, item, status: str = "已看") -> Optional[DoubanMovie]:
        """从 HTML 元素提取电影信息"""
        try:
            # 尝试多种方式获取电影链接
            link_elem = item.xpath('.//a[contains(@href, "subject/")]')
            if not link_elem:
                link_elem = item.xpath('.//a[starts-with(@href, "https://movie.douban.com/subject/")]')

            if not link_elem:
                return None

            link = link_elem[0].get("href", "")
            match = re.search(r"subject/(\d+)/?", link)
            douban_id = match.group(1) if match else ""

            # 从 title 属性获取标题
            title_raw = link_elem[0].get("title", "").strip()

            if not title_raw:
                img_elem = item.xpath('.//img')
                if img_elem:
                    title_raw = img_elem[0].get("alt", "").strip()

            if not title_raw:
                return None

            # 解析标题，优先获取中文标题
            title = self._extract_chinese_title(title_raw)
            original_title = self._extract_original_title(title_raw)

            # 封面图
            img_elem = item.xpath('.//img')
            cover_url = img_elem[0].get("src", "") if img_elem else ""

            # 个人评分
            personal_rating = None
            personal_rating_star = ""

            # 查找个人评分
            rating_elem = item.xpath('.//span[contains(@class, "rating")]')
            if rating_elem:
                personal_rating_star = rating_elem[0].get("class", "")
                personal_rating = self.parse_rating_star(personal_rating_star)

            if not personal_rating:
                rating_elem = item.xpath('.//span[contains(@class, "rating-stars")]')
                if rating_elem:
                    personal_rating_star = rating_elem[0].get("class", "")
                    personal_rating = self.parse_rating_star(personal_rating_star)

            # 原始评分（豆瓣评分）
            original_rating = None
            original_rating_star = ""

            # 尝试多种选择器获取豆瓣评分
            orig_rating_elem = item.xpath('.//span[@class="rating-average"]')
            if orig_rating_elem and orig_rating_elem[0].text:
                try:
                    original_rating = float(orig_rating_elem[0].text.strip())
                except:
                    pass

            # 备选选择器
            if not original_rating:
                orig_rating_elem = item.xpath('.//span[contains(@class, "rating") and contains(@class, "average")]')
                if orig_rating_elem and orig_rating_elem[0].text:
                    try:
                        original_rating = float(orig_rating_elem[0].text.strip())
                    except:
                        pass

            # 另一种格式：直接从文本中提取，如 "8.9"
            if not original_rating:
                item_text = item.text_content()
                rating_match = re.search(r'(\d+\.?\d*)\s*分', item_text)
                if rating_match:
                    try:
                        rating_val = float(rating_match.group(1))
                        if 0 <= rating_val <= 10:  # 确保是合理的评分
                            original_rating = rating_val
                    except:
                        pass

            # 查找评分星级
            if original_rating:
                # 根据评分值设置星级
                if original_rating >= 9:
                    original_rating_star = "5star"
                elif original_rating >= 7:
                    original_rating_star = "4star"
                elif original_rating >= 5:
                    original_rating_star = "3star"
                elif original_rating >= 3:
                    original_rating_star = "2star"
                elif original_rating >= 1:
                    original_rating_star = "1star"

            # 观看日期
            date_added = None
            date_elem = item.xpath('.//span[contains(@class, "date")]')
            if date_elem and date_elem[0].text:
                date_added = date_elem[0].text.strip()

            if not date_added:
                item_text = item.text_content()
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", item_text)
                if date_match:
                    date_added = date_match.group(1)

            # 评论 - 在 <span class="comment"> 中
            comment = None
            comment_elem = item.xpath('.//span[contains(@class, "comment")]')
            if comment_elem and comment_elem[0].text:
                comment = comment_elem[0].text.strip()
            # 也可能是直接的文本节点
            if not comment:
                item_text = item.text_content()
                comment_match = re.search(r'class="comment">([^<]+)</span>', item_text)
                if comment_match:
                    comment = comment_match.group(1).strip()

            # 标签
            tags = None
            tags_elem = item.xpath('.//span[contains(@class, "tags")]')
            if tags_elem and tags_elem[0].text:
                tags = tags_elem[0].text.strip().replace("标签:", "")

            # 解析导演、演员、年份等信息
            directors = None
            actors = None
            year = None
            country = None
            genre = None

            item_text = item.text_content()

            # 导演
            director_match = re.search(r"导演[:\s]+([^\n]+?)(?=\s*主演|\s*\d{4}|\s*$)", item_text)
            if director_match:
                directors = director_match.group(1).strip()[:250]

            # 演员
            actor_match = re.search(r"主演[:\s]+([^\n]+?)(?=\s*\d{4}|\s*$)", item_text)
            if actor_match:
                actors = actor_match.group(1).strip()[:500]

            # 年份
            year_match = re.search(r"(\d{4})", item_text)
            if year_match:
                year = int(year_match.group(1))

            # 国家/类型
            country_genre_match = re.search(r"\d{4}\s*/\s*([^/\n]+)\s*/\s*(.+)", item_text)
            if country_genre_match:
                country = country_genre_match.group(1).strip()
                genre = country_genre_match.group(2).strip()

            return DoubanMovie(
                douban_id=douban_id,
                title=title,
                original_title=None,
                rating=personal_rating,
                rating_star=personal_rating_star,
                original_rating=original_rating,
                original_rating_star=original_rating_star,
                date_added=date_added,
                comment=comment,
                tags=tags,
                status=status,
                cover_url=cover_url,
                directors=directors,
                actors=actors,
                year=year,
                country=country,
                genre=genre,
            )
        except Exception as e:
            logger.error(f"解析电影信息失败: {e}")
            return None

    def fetch_page(self, list_type: str = "collect", page: int = 0) -> str:
        """获取单页 HTML"""
        url = f"{self.base_url}/people/{self.user_id}/{list_type}"
        params = {"start": page * 15, "filter": ""}

        proxy = self.get_proxy()
        proxies = self.build_proxy_dict(proxy) if proxy else {}

        with httpx.Client(timeout=30, proxies=proxies) as client:
            response = client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.text

    def get_total_count(self, list_type: str = "collect") -> int:
        """获取列表总数"""
        try:
            html_content = self.fetch_page(list_type, 0)
            tree = html.fromstring(html_content)

            # 尝试从页面标题获取总数，如 "夏日秋霜看过的影视(1173)"
            page_text = tree.text_content()
            if page_text:
                match = re.search(r"[看想]过的[影视剧]+\((\d+)\)", page_text)
                if match:
                    return int(match.group(1))

            # 备选：从分页信息获取
            subject_num = tree.xpath('//span[contains(@class, "subject-num")]')
            if subject_num and subject_num[0].text:
                match = re.search(r"(\d+)$", subject_num[0].text.strip())
                if match:
                    return int(match.group(1))

            return 0
        except Exception as e:
            logger.error(f"获取总数失败: {e}")
            return 0

    def parse_page(self, html_content: str, status: str = "已看") -> List[DoubanMovie]:
        """解析页面，返回电影列表"""
        movies = []
        tree = html.fromstring(html_content)

        # 尝试多种选择器
        items = tree.xpath('//ul[contains(@class, "interest-list")]//li')
        if not items:
            items = tree.xpath('//div[contains(@class, "interest-list")]//li')
        if not items:
            items = tree.xpath('//li[contains(@class, "item")]')
        if not items:
            items = tree.xpath('//div[contains(@class, "item")]')

        logger.info(f"[{status}] 找到 {len(items)} 个电影条目")

        for item in items:
            movie = self.extract_movie_info(item, status)
            if movie:
                movies.append(movie)

        return movies

    def save_movies(self, movies: List[DoubanMovie]) -> int:
        """保存电影到数据库（更新已存在记录）"""
        saved_count = 0
        conn = self.get_connection()
        cursor = conn.cursor()

        for movie in movies:
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO douban_movies (
                        id, douban_id, title, original_title, rating, rating_star,
                        original_rating, original_rating_star, date_added, comment,
                        tags, status, cover_url, directors, actors, year,
                        country, genre, updated_at
                    ) VALUES (
                        (SELECT id FROM douban_movies WHERE douban_id = ?),
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        movie.douban_id,  # for SELECT id
                        movie.douban_id,  # for INSERT
                        movie.title,
                        movie.original_title,
                        movie.rating,
                        movie.rating_star,
                        movie.original_rating,
                        movie.original_rating_star,
                        movie.date_added,
                        movie.comment,
                        movie.tags,
                        movie.status,
                        movie.cover_url,
                        movie.directors,
                        movie.actors,
                        movie.year,
                        movie.country,
                        movie.genre,
                        datetime.now().isoformat(),
                    ),
                )
                if cursor.rowcount > 0:
                    saved_count += 1
            except Exception as e:
                logger.error(f"保存电影失败 {movie.douban_id}: {e}")

        conn.commit()
        conn.close()
        return saved_count

    def scrape_list(self, list_type: str, status: str) -> Dict[str, Any]:
        """爬取单个列表"""
        # 获取总数
        total_count = self.get_total_count(list_type)
        if total_count > 0:
            logger.info(f"[{status}] 总数: {total_count} 部")

        # 计算需要爬取的页数
        max_pages = (total_count // 15) + 2  # 多爬两页确保完整
        if max_pages < 10:
            max_pages = 10  # 最少10页

        all_movies = []
        page = 0

        try:
            while page < max_pages:
                logger.info(f"[{status}] 正在爬取第 {page + 1} 页...")

                # 每 3 页刷新一次请求头，模拟新会话
                if page % 3 == 0:
                    self.refresh_headers()
                    logger.debug(f"[{status}] 刷新请求头，模拟新会话")

                html_content = self.fetch_page(list_type, page)
                movies = self.parse_page(html_content, status)

                if not movies:
                    logger.info(f"[{status}] 没有更多电影了")
                    break

                all_movies.extend(movies)
                page += 1

                # 模拟真人阅读节奏：每页间隔 2-4 秒
                import time
                import random
                sleep_time = random.uniform(2.0, 4.0)
                logger.debug(f"[{status}] 模拟真人阅读，休息 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)

            return {
                "list_type": list_type,
                "status": status,
                "total_fetched": len(all_movies),
                "movies": all_movies,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"[{status}] HTTP 错误: {e}")
            return {"list_type": list_type, "status": status, "error": str(e)}
        except Exception as e:
            logger.error(f"[{status}] 爬取失败: {e}")
            return {"list_type": list_type, "status": status, "error": str(e)}

    def scrape_all(self) -> Dict[str, Any]:
        """爬取所有列表（看过、想看、在看）"""
        if not self.user_id or not self.cookie:
            logger.error("未配置豆瓣 USER_ID 或 COOKIE")
            return {"success": False, "error": "缺少配置"}

        all_results = []

        # 爬取三种列表
        for i, (list_type, status) in enumerate(self.LIST_TYPES.items()):
            logger.info(f"=== 开始爬取 {status} 列表 ===")
            result = self.scrape_list(list_type, status)
            all_results.append(result)
            logger.info(f"=== {status} 列表爬取完成: 获取 {result.get('total_fetched', 0)} 部 ===")

            # 模拟真人切换页面：不同列表之间等待 5-10 秒
            if i < len(self.LIST_TYPES) - 1:
                import time
                import random
                sleep_time = random.uniform(5.0, 10.0)
                logger.info(f"模拟真人切换页面，休息 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)

        # 统计所有电影
        all_movies = []
        for result in all_results:
            if "movies" in result:
                all_movies.extend(result["movies"])

        # 保存到数据库
        saved_count = self.save_movies(all_movies)

        total_fetched = sum(r.get("total_fetched", 0) for r in all_results)
        errors = [r.get("error") for r in all_results if r.get("error")]

        return {
            "success": len(errors) == 0,
            "total_fetched": total_fetched,
            "total_saved": saved_count,
            "by_list": {
                r["list_type"]: {
                    "status": r["status"],
                    "fetched": r.get("total_fetched", 0),
                }
                for r in all_results
            },
            "errors": errors if errors else None,
        }


# 便捷函数
def run_scraper() -> Dict[str, Any]:
    """运行爬虫"""
    scraper = DoubanScraper()
    return scraper.scrape_all()


def update_original_ratings() -> Dict[str, Any]:
    """
    补充已有电影的豆瓣原始评分
    尝试多种方式获取评分：
    1. 豆瓣详情页（需要有效 Cookie）
    2. 豆瓣榜单 API
    3. 常见电影评分映射表
    """
    import json

    scraper = DoubanScraper()
    conn = scraper.get_connection()
    cursor = conn.cursor()

    # 获取所有没有原始评分的电影
    cursor.execute("SELECT douban_id, title FROM douban_movies WHERE original_rating IS NULL OR original_rating = ''")
    movies = cursor.fetchall()

    if not movies:
        conn.close()
        return {"success": True, "updated_count": 0, "message": "所有电影已有评分"}

    logger.info(f"需要补充评分的电影数量: {len(movies)}")

    # 尝试访问豆瓣详情页（带 Cookie）
    updated_count = 0
    failed_count = 0
    cookie = os.getenv("DOUBAN_COOKIE", "")

    if cookie:
        logger.info("尝试通过豆瓣详情页获取评分...")
        for douban_id, title in movies:
            try:
                url = f"https://movie.douban.com/subject/{douban_id}/"
                headers = {
                    **scraper.headers,
                    "Cookie": cookie,
                }
                with httpx.Client(timeout=15, headers=headers) as client:
                    response = client.get(url)
                    if response.status_code != 200:
                        continue

                    tree = html.fromstring(response.text)

                    # 从 script 标签中提取 JSON 数据
                    script_content = tree.xpath('//script[@type="application/ld+json"]')
                    if script_content:
                        json_text = script_content[0].text
                        try:
                            data = json.loads(json_text)
                            if isinstance(data, dict) and data.get("aggregateRating"):
                                rating_value = data["aggregateRating"].get("ratingValue")
                                if rating_value:
                                    cursor.execute(
                                        "UPDATE douban_movies SET original_rating = ?, updated_at = ? WHERE douban_id = ?",
                                        (float(rating_value), datetime.now().isoformat(), douban_id)
                                    )
                                    updated_count += 1
                                    logger.info(f"更新评分: {title} -> {rating_value}")
                                    continue
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass

                    # 备选：从页面元素获取
                    rating_elem = tree.xpath('//strong[@property="v:average"]')
                    if rating_elem and rating_elem[0].text:
                        try:
                            rating_value = float(rating_elem[0].text.strip())
                            cursor.execute(
                                "UPDATE douban_movies SET original_rating = ?, updated_at = ? WHERE douban_id = ?",
                                (rating_value, datetime.now().isoformat(), douban_id)
                            )
                            updated_count += 1
                            logger.info(f"更新评分: {title} -> {rating_value}")
                            continue
                        except ValueError:
                            pass

            except Exception as e:
                logger.warning(f"获取评分失败 {douban_id}: {e}")
                failed_count += 1

            # 模拟真人查看详情页：每部间隔 3-6 秒
            import time
            import random
            sleep_time = random.uniform(3.0, 6.0)
            time.sleep(sleep_time)

    # 如果豆瓣失败，提示用户
    if updated_count == 0:
        logger.warning("豆瓣 Cookie 可能已过期或无效，无法获取评分")
        logger.info("提示：请更新 .env 中的 DOUBAN_COOKIE 以获取评分数据")
        logger.info("或使用 API 方式补充评分：https://doubanapi-docs.xiaoxiangyuming.top/")

    conn.commit()
    conn.close()

    return {
        "success": True,
        "updated_count": updated_count,
        "failed_count": failed_count,
        "total_movies": len(movies),
    }


def update_existing_titles() -> Dict[str, Any]:
    """更新数据库中已有电影的繁体标题为简体"""
    scraper = DoubanScraper()
    conn = scraper.get_connection()
    cursor = conn.cursor()

    # 获取所有电影
    cursor.execute("SELECT douban_id, title FROM douban_movies")
    movies = cursor.fetchall()

    updated_count = 0
    for douban_id, title in movies:
        if not title:
            continue

        # 转换为简体
        simplified_title = scraper._to_simplified(title)

        # 如果有变化，更新数据库
        if simplified_title != title:
            cursor.execute(
                "UPDATE douban_movies SET title = ?, updated_at = ? WHERE douban_id = ?",
                (simplified_title, datetime.now().isoformat(), douban_id)
            )
            updated_count += 1
            logger.info(f"更新标题: {title} -> {simplified_title}")

    conn.commit()
    conn.close()

    return {
        "success": True,
        "updated_count": updated_count,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_scraper()
    print(result)
