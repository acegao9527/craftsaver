from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import sqlite3
import os
import sys
sys.path.insert(0, "/app")
from src.models.douban import DoubanMovieInDB, MovieStats

router = APIRouter(prefix="/api/douban", tags=["Douban"])

DB_PATH = os.getenv("SQLITE_DB_PATH", "data/savehelper.db")


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def row_to_movie(row) -> dict:
    """将数据库行转换为电影字典"""
    return {
        "id": row[0],
        "douban_id": row[1],
        "title": row[2],
        "original_title": row[3],
        "rating": row[4],
        "rating_star": row[5],
        "original_rating": row[6],
        "original_rating_star": row[7],
        "date_added": row[8],
        "comment": row[9],
        "tags": row[10],
        "status": row[11],
        "cover_url": row[12],
        "directors": row[13],
        "actors": row[14],
        "year": row[15],
        "country": row[16],
        "genre": row[17],
        "created_at": row[18] if len(row) > 18 else None,
        "updated_at": row[19] if len(row) > 19 else None,
    }


@router.get("/movies")
async def list_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    status: Optional[str] = Query(None, pattern="^(想看|在看|已看)?$"),
    genre: Optional[str] = None,
    year_from: Optional[int] = Query(None, ge=1900, le=2100),
    year_to: Optional[int] = Query(None, ge=1900, le=2100),
    sort_by: str = Query("date_added", pattern="^(date_added|rating|year)$"),
):
    """查询电影列表"""
    offset = (page - 1) * page_size

    where_clauses = []
    params = []

    if keyword:
        where_clauses.append("(title LIKE ? OR original_title LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if min_rating is not None:
        where_clauses.append("rating >= ?")
        params.append(min_rating)

    if status:
        where_clauses.append("status = ?")
        params.append(status)

    if genre:
        where_clauses.append("genre LIKE ?")
        params.append(f"%{genre}%")

    if year_from is not None:
        where_clauses.append("(year IS NULL OR year >= ?)")
        params.append(year_from)

    if year_to is not None:
        where_clauses.append("(year IS NULL OR year <= ?)")
        params.append(year_to)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # 排序
    order_sql = {
        "date_added": "date_added DESC",
        "rating": "rating DESC NULLS LAST",
        "year": "year DESC",
    }.get(sort_by, "date_added DESC")

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM douban_movies WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # 查询列表
        sql = f"""
            SELECT id, douban_id, title, original_title, rating, rating_star,
                   original_rating, original_rating_star, date_added, comment,
                   tags, status, cover_url, directors, actors, year, country,
                   genre, created_at, updated_at
            FROM douban_movies
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """
        cursor.execute(sql, params + [page_size, offset])
        rows = cursor.fetchall()

    return {
        "code": 200,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "movies": [row_to_movie(row) for row in rows],
        },
    }


@router.get("/movies/{douban_id}")
async def get_movie(douban_id: str):
    """获取电影详情"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, douban_id, title, original_title, rating, rating_star,
                   original_rating, original_rating_star, date_added, comment,
                   tags, status, cover_url, directors, actors, year, country,
                   genre, created_at, updated_at
            FROM douban_movies WHERE douban_id = ?
            """,
            (douban_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="电影不存在")

    return {
        "code": 200,
        "data": row_to_movie(row),
    }


@router.get("/stats")
async def get_stats() -> MovieStats:
    """获取统计信息"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 总数
        cursor.execute("SELECT COUNT(*) FROM douban_movies")
        total_count = cursor.fetchone()[0]

        # 平均评分
        cursor.execute("SELECT AVG(rating) FROM douban_movies WHERE rating IS NOT NULL")
        avg_rating = cursor.fetchone()[0]

        # 评分分布
        cursor.execute("""
            SELECT
                CASE
                    WHEN rating >= 5 THEN '5星'
                    WHEN rating >= 4 THEN '4星'
                    WHEN rating >= 3 THEN '3星'
                    WHEN rating >= 2 THEN '2星'
                    WHEN rating >= 1 THEN '1星'
                    ELSE '未评分'
                END as star,
                COUNT(*) as count
            FROM douban_movies
            GROUP BY star
        """)
        rating_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # 状态分布
        cursor.execute("""
            SELECT COALESCE(status, '未知'), COUNT(*) as count
            FROM douban_movies
            GROUP BY status
        """)
        status_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # 类型分布
        cursor.execute("""
            SELECT genre, COUNT(*) as count
            FROM douban_movies
            WHERE genre IS NOT NULL
            GROUP BY genre
            ORDER BY count DESC
            LIMIT 10
        """)
        genre_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # 年份分布
        cursor.execute("""
            SELECT year, COUNT(*) as count
            FROM douban_movies
            WHERE year IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
        """)
        year_dist = {str(row[0]): row[1] for row in cursor.fetchall()}

    return MovieStats(
        total_count=total_count,
        avg_rating=round(avg_rating, 2) if avg_rating else None,
        rating_distribution=rating_dist,
        status_distribution=status_dist,
        genre_distribution=genre_dist,
        year_distribution=year_dist,
    )


@router.post("/refresh")
async def refresh_movies():
    """手动触发爬取豆瓣记录"""
    from src.services.douban_scraper import run_scraper

    result = run_scraper()

    if result.get("success"):
        return {
            "code": 200,
            "data": result,
            "message": f"成功获取 {result.get('total_fetched', 0)} 部电影，新增 {result.get('total_saved', 0)} 部",
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "爬取失败"))


@router.post("/update-ratings")
async def update_ratings():
    """
    补充已有电影的豆瓣原始评分
    - 先校验 Cookie 有效性
    - 异步执行，不阻塞返回
    """
    import asyncio
    import httpx
    import os

    # 1. 校验 Cookie 有效性
    cookie = os.getenv("DOUBAN_COOKIE", "")
    if not cookie:
        raise HTTPException(status_code=400, detail="未配置豆瓣 Cookie，请先在 .env 中设置 DOUBAN_COOKIE")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Cookie": cookie,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://movie.douban.com/people/", headers=headers)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=403,
                    detail="豆瓣 Cookie 已过期或无效，请重新获取并更新 .env 中的 DOUBAN_COOKIE"
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"校验 Cookie 失败: {str(e)}")

    # 2. 异步触发评分更新任务
    async def run_update_task():
        """异步执行评分更新，并在日志中打印明细"""
        import logging
        from src.services.douban_scraper import DoubanScraper

        logger = logging.getLogger("douban.rating_update")
        logger.info("=" * 60)
        logger.info("开始更新电影原始评分")
        logger.info("=" * 60)

        scraper = DoubanScraper()
        conn = scraper.get_connection()
        cursor = conn.cursor()

        # 获取需要更新的电影
        cursor.execute("SELECT douban_id, title FROM douban_movies WHERE original_rating IS NULL OR original_rating = ''")
        movies = cursor.fetchall()
        total_movies = len(movies)

        logger.info(f"待更新评分的电影数量: {total_movies}")

        if not movies:
            logger.info("所有电影已有评分，无需更新")
            conn.close()
            return {"success": True, "updated_count": 0, "message": "所有电影已有评分"}

        updated_count = 0
        failed_count = 0

        for i, (douban_id, title) in enumerate(movies):
            try:
                url = f"https://movie.douban.com/subject/{douban_id}/"
                response = await scraper.async_fetch(url, headers)

                if response.status_code != 200:
                    logger.warning(f"[{i+1}/{total_movies}] 跳过 {title} (HTTP {response.status_code})")
                    failed_count += 1
                    continue

                # 解析评分
                from lxml import html
                tree = html.fromstring(response.text)

                script_content = tree.xpath('//script[@type="application/ld+json"]')
                rating_value = None

                if script_content:
                    import json
                    try:
                        data = json.loads(script_content[0].text)
                        if isinstance(data, dict) and data.get("aggregateRating"):
                            rating_value = data["aggregateRating"].get("ratingValue")
                    except:
                        pass

                if not rating_value:
                    rating_elem = tree.xpath('//strong[@property="v:average"]')
                    if rating_elem and rating_elem[0].text:
                        try:
                            rating_value = float(rating_elem[0].text.strip())
                        except:
                            pass

                if rating_value:
                    cursor.execute(
                        "UPDATE douban_movies SET original_rating = ?, updated_at = datetime('now') WHERE douban_id = ?",
                        (float(rating_value), douban_id)
                    )
                    logger.info(f"[{i+1}/{total_movies}] ✓ {title} -> 评分: {rating_value}")
                    updated_count += 1
                else:
                    logger.warning(f"[{i+1}/{total_movies}] ✗ {title} -> 未找到评分")
                    failed_count += 1

            except Exception as e:
                logger.error(f"[{i+1}/{total_movies}] ✗ {title} -> 错误: {str(e)[:100]}")
                failed_count += 1

            # 模拟真人访问间隔
            import random
            await asyncio.sleep(random.uniform(3.0, 6.0))

        conn.commit()
        conn.close()

        logger.info("=" * 60)
        logger.info(f"评分更新完成: 成功 {updated_count}, 失败 {failed_count}, 总计 {total_movies}")
        logger.info("=" * 60)

    # 启动异步任务（不等待完成）
    asyncio.create_task(run_update_task())

    return {
        "code": 200,
        "message": "评分更新任务已启动，请查看日志了解进度",
    }
